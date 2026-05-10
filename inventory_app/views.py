import io
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.conf import settings
from .models import Job, InventoryUsageLog, InventoryItem, WarehouseLocation, StockLevel, JobImage
from .forms import InventoryUsageLogForm, InventoryUsageLogFormSet

try:
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
except ImportError:
    pass  # User is instructed to install reportlab and pypdf

@login_required
def job_list_view(request):
    """View to list all pending jobs for the logged in worker."""
    # Use assigned_workers M2M so multi-worker jobs are visible
    jobs = Job.objects.filter(assigned_workers=request.user, status='pending').distinct()
    
    # We also might want to show in_progress jobs
    in_progress = Job.objects.filter(assigned_workers=request.user, status='in_progress').distinct()
    
    # Fetch completed jobs for history
    completed = Job.objects.filter(assigned_workers=request.user, status='completed').order_by('-execution_date').distinct()
    
    context = {
        'pending_jobs': jobs,
        'in_progress_jobs': in_progress,
        'completed_jobs': completed
    }
    return render(request, 'inventory_app/job_list.html', context)

@never_cache
@login_required
def job_detail_view(request, job_id):
    """
    View to see specific container job details and log multiple items used.
    Requires:
    1. Selection of a Warehouse Location (mandatory)
    2. Multiple InventoryUsageLog entries (at least one)
    Each log entry deducts from the selected warehouse's StockLevel.
    """
    job = get_object_or_404(Job, id=job_id, assigned_workers=request.user)

    if job.status == 'completed':
        return redirect('job_list')

    # Job stays 'pending' until the worker actually submits the form.

    warehouse_locations = WarehouseLocation.objects.all()
    # The JS uses 'inventoryusagelog_set' as its field-name prefix,
    # so the Django formset MUST use the same prefix to parse POST data.
    FORMSET_PREFIX = 'inventoryusagelog_set'

    if request.method == 'POST':
        warehouse_location_id = request.POST.get('warehouse_location')

        # Validate warehouse location
        if not warehouse_location_id:
            return JsonResponse({'success': False, 'error': 'Please select a Warehouse Location.'}, status=400)

        try:
            warehouse_location = WarehouseLocation.objects.get(id=warehouse_location_id)
        except WarehouseLocation.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid Warehouse Location selected.'}, status=400)

        # Validate at least one image is uploaded
        has_images = any(request.FILES.get(f'job_image_{i}') for i in range(5))
        if not has_images:
            return JsonResponse({'success': False, 'error': 'Please upload at least one photo proof.'}, status=400)

        # Process formset — prefix must match what the JS sends
        formset = InventoryUsageLogFormSet(
            request.POST,
            queryset=InventoryUsageLog.objects.none(),
            prefix=FORMSET_PREFIX,
        )

        if formset.is_valid():
            with transaction.atomic():
                # --- Pre-flight stock validation ---
                from collections import defaultdict
                from decimal import Decimal
                item_taken_totals = defaultdict(Decimal)
                
                for form in formset.forms:
                    cd = form.cleaned_data
                    if not cd or cd.get('DELETE', False):
                        continue
                    if not cd.get('item'):
                        continue
                    item_taken_totals[cd['item']] += cd.get('amount_taken', Decimal('0'))
                
                stock_errors = []
                for item, total_taken in item_taken_totals.items():
                    try:
                        stock_level = StockLevel.objects.get(item=item, location=warehouse_location)
                        available = Decimal(str(stock_level.quantity))
                        if total_taken > available:
                            val_taken = total_taken.normalize()
                            val_avail = available.normalize()
                            stock_errors.append(f"Not enough stock for {item.name}. Available: {val_avail}, Attempting to take: {val_taken}.")
                    except StockLevel.DoesNotExist:
                        stock_errors.append(f"No stock record found for {item.name} at {warehouse_location.name}.")

                if stock_errors:
                    return JsonResponse({'success': False, 'error': " | ".join(stock_errors)}, status=400)
                # -----------------------------------

                saved_logs = []
                image_files = [f for key in request.FILES for f in request.FILES.getlist(key) if key.startswith('job_image_') or key == 'completion_images']
                # Also check for multiple files under completion_images key
                multi_images = request.FILES.getlist('completion_images')
                single_images = [request.FILES.get(f'job_image_{i}') for i in range(5) if request.FILES.get(f'job_image_{i}')]
                all_images = multi_images if multi_images else single_images

                for form in formset.forms:
                    cd = form.cleaned_data
                    # Skip blank/deleted forms
                    if not cd or cd.get('DELETE', False):
                        continue
                    if not cd.get('item'):  # item is required
                        continue

                    log = form.save(commit=False)
                    log.job = job

                    from decimal import Decimal
                    log.amount_taken = round(Decimal(str(log.amount_taken)), 2)
                    log.amount_used = round(Decimal(str(log.amount_used)), 2)
                    log.amount_returned = round(Decimal(str(log.amount_returned)), 2)

                    # Attach first image to the first log (backwards compat)
                    if not saved_logs and all_images:
                        log.photo_proof = all_images[0]

                    log.save()
                    saved_logs.append(log)

                    # Deduct from StockLevel (decimal-safe)
                    from decimal import Decimal
                    try:
                        stock_level = StockLevel.objects.get(
                            item=log.item,
                            location=warehouse_location
                        )
                        new_qty = stock_level.quantity - float(log.amount_used)
                        stock_level.quantity = max(0, int(new_qty)) if isinstance(stock_level.quantity, int) else max(Decimal('0'), Decimal(str(new_qty)))
                        stock_level.save()
                    except StockLevel.DoesNotExist:
                        pass  # No stock record — admin can reconcile later

                if saved_logs:
                    job.status = 'completed'
                    job.save()
                    # Save all uploaded images as JobImage records
                    for img_file in all_images:
                        JobImage.objects.create(job=job, image=img_file)
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully logged {len(saved_logs)} item(s) and completed job {job.container_number}.'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'No valid items to log. Please fill in at least one item with Taken and Used amounts.'
                    }, status=400)
        else:
            # Collect formset errors into a readable message
            error_msgs = []
            for ferr in formset.errors:
                for field, errs in ferr.items():
                    if field != '__all__':
                        error_msgs.extend(errs)
            if formset.non_form_errors():
                error_msgs.extend(formset.non_form_errors())
            error_text = ' | '.join(dict.fromkeys(error_msgs)) if error_msgs else 'Please correct the errors in the form.'
            return JsonResponse({'success': False, 'error': error_text}, status=400)
    else:
        formset = InventoryUsageLogFormSet(
            queryset=InventoryUsageLog.objects.none(),
            prefix=FORMSET_PREFIX,
        )

    context = {
        'job': job,
        'formset': formset,
        'warehouse_locations': warehouse_locations,
        'inventory_items': InventoryItem.objects.all().order_by('name'),
    }
    return render(request, 'inventory_app/job_detail.html', context)

@login_required
def mark_job_completed(request, job_id):
    job = get_object_or_404(Job, id=job_id, assigned_to=request.user)
    if not job.usage_logs.exists():
        messages.error(request, "Cannot mark as complete without logging usage data.")
        return redirect('job_detail', job_id=job.id)
    job.status = 'completed'
    job.save()
    messages.success(request, f"Job {job.container_number} marked as completed.")
    return redirect('job_list')

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('job_list')
    else:
        form = UserCreationForm()
    return render(request, 'inventory_app/signup.html', {'form': form})

def login_choice_view(request):
    """Unified login view for both worker and admin."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('office_dashboard')
        else:
            return redirect('job_list')
    context = {'login_type': 'worker'}
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        login_type = request.POST.get('login_type', 'worker')
        context['login_type'] = login_type
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if login_type == 'admin':
                if user.is_staff:
                    login(request, user)
                    return redirect('office_dashboard')
                else:
                    messages.error(request, "Access denied. Admin account required.")
            else:
                login(request, user)
                return redirect('job_list')
        else:
            messages.error(request, "Invalid credentials. Please check your username and password.")
    
    return render(request, 'inventory_app/login_choice.html', context)

def admin_login_view(request):
    """Custom admin login view that validates staff status."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('office_dashboard')
        else:
            return redirect('job_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                next_page = request.GET.get('next', 'office_dashboard')
                return redirect(next_page)
            else:
                messages.error(request, "Access denied. Admin account required.")
                return render(request, 'inventory_app/login.html', {'is_admin': True})
        else:
            messages.error(request, "Invalid credentials.")
            return render(request, 'inventory_app/login.html', {'is_admin': True})
    
    return render(request, 'inventory_app/login.html', {'is_admin': True})

def worker_login_view(request):
    """Custom worker login view."""
    if request.user.is_authenticated:
        return redirect('job_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_page = request.GET.get('next', 'job_list')
            return redirect(next_page)
        else:
            messages.error(request, "Invalid credentials.")
            return render(request, 'inventory_app/login.html', {'is_admin': False})
    
    return render(request, 'inventory_app/login.html', {'is_admin': False})

def map_box(box_dict, text, bold=False, font_size=9, max_lines=1, line_gap=11):
    """Directly maps dictionary from the website into ReportLab format."""
    return {
        'text': str(text) if text else '',  # Ensure it's a string, avoid None
        'x': box_dict['x'],
        'y': box_dict['y'],                 # Direct Y mapping
        'max_width': box_dict['width'],
        'bold': bold,
        'font_size': font_size,
        'max_lines': max_lines,
        'line_gap': line_gap
    }

@login_required
def generate_certificate_pdf(request, job_id):
    """Generates a PDF certificate for a completed job."""
    job = get_object_or_404(Job, pk=job_id)

    # Use exact path logic (adjust if your path is slightly different)
    template_path = os.path.join(settings.MEDIA_ROOT, 'certificate', 'blank_certificate.pdf')
    if not os.path.exists(template_path):
        # Fallback to the absolute path if relative fails
        template_path = r"C:\Users\AADITYA\Documents\Stock Maientanance\media\certificate\blank_certificate.pdf"
        if not os.path.exists(template_path):
            return HttpResponse(f"Blank certificate template not found at exact path: {template_path}", status=404)

    # Get background page dimensions dynamically
    with open(template_path, 'rb') as template_file:
        background = PdfReader(io.BytesIO(template_file.read()))
        page = background.pages[0]
        page_width = float(page.mediabox.right)
        page_height = float(page.mediabox.top)
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Format Dates safely
    commenced = job.datetime_commenced.strftime('%d-%b-%Y %I:%M %p') if job.datetime_commenced else ''
    completed = job.datetime_completed.strftime('%d-%b-%Y %I:%M %p') if job.datetime_completed else ''
    sign_date = job.certificate_sign_date.strftime('%d-%b-%Y') if job.certificate_sign_date else ''

    # ── Text Wrapping Helper Function ──
    def draw_value(text, x, y, bold=False, font_size=9, max_width=None, max_lines=1, line_gap=11):
        text = str(text or '').strip()
        if not text:
            return

        font_name = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font_name, font_size)

        lines = []
        for raw_line in text.splitlines() or [text]:
            words = raw_line.split()
            if not words:
                lines.append("")
                continue

            line = words[0]
            for word in words[1:]:
                candidate = f"{line} {word}"
                if max_width and c.stringWidth(candidate, font_name, font_size) > max_width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)

        for idx, line in enumerate(lines[:max_lines]):
            if max_width:
                while line and c.stringWidth(line, font_name, font_size) > max_width:
                    line = line[:-1]
            c.drawString(x, y - (idx * line_gap), line)

    # ── Coordinate Map Strategy ──
    pdf_data_map = {
        'cert_number': map_box({"page":1,"x":217,"y":699,"width":86,"height":12}, job.certificate_number, bold=True),
        'provider_id': map_box({"page":1,"x":477,"y":699,"width":92,"height":13}, job.treatment_provider_id, bold=True),
        
        'consignment_link': map_box({"page":1,"x":220,"y":667,"width":345,"height":12}, job.consignment_link),
        'container_box': map_box({"page":1,"x":222,"y":652,"width":345,"height":10}, job.container_number),
        'seal_numbers': map_box({"page":1,"x":221,"y":631,"width":345,"height":16}, job.seal_numbers),
        
        'client_name': map_box({"page":1,"x":222,"y":620,"width":329,"height":12}, job.client.name if job.client else ''),
        'client_address': map_box({"page":1,"x":225,"y":594,"width":341,"height":21}, job.client.address if job.client else '', max_lines=2),
        'consignee_name': map_box({"page":1,"x":222,"y":577,"width":336,"height":11}, job.client.name if job.client else ''),
        'consignee_address': map_box({"page":1,"x":222,"y":559,"width":337,"height":15}, job.client.address if job.client else '', max_lines=2),
        
        'commodity_desc': map_box({"page":1,"x":222,"y":548,"width":346,"height":9}, job.commodity_description),
        'commodity_origin': map_box({"page":1,"x":218,"y":518,"width":81,"height":22}, job.commodity_country_of_origin),
        'commodity_quantity': map_box({"page":1,"x":401,"y":518,"width":163,"height":22}, job.quantity_pkgs),
        'destination_country': map_box({"page":1,"x":399,"y":504,"width":166,"height":10}, job.destination_country),
        'port_of_loading': map_box({"page":1,"x":156,"y":503,"width":100,"height":11}, job.port_of_loading),
        
        # Fields keeping old manual formatting:
        'target_other_text': {'text': job.target_other, 'x': 120, 'y': 449},
        'prescribed_dose': {'text': job.prescribed_dose, 'x': 250, 'y': 418},
        'prescribed_exposure': {'text': job.prescribed_exposure, 'x': 360, 'y': 418},
        'prescribed_temp': {'text': job.prescribed_temp, 'x': 470, 'y': 418},
        'applied_dose': {'text': job.applied_dose, 'x': 250, 'y': 387},
        'applied_exposure': {'text': job.applied_exposure, 'x': 360, 'y': 387},
        'applied_temp': {'text': job.applied_temp, 'x': 470, 'y': 387},
        'operator_name': {'text': job.operator_name, 'x': 250, 'y': 170},
        
        # Back to JSON mappings:
        'fumigation_street': map_box({"page":1,"x":310,"y":358,"width":250,"height":12}, job.fumigation_street),
        'fumigation_city': map_box({"page":1,"x":311,"y":341,"width":247,"height":15}, f"{job.fumigation_city or ''} {job.fumigation_country or ''}".strip()),
        'fumigation_postcode': map_box({"page":1,"x":443,"y":327,"width":121,"height":10}, job.fumigation_postcode),
        
        'date_commenced': map_box({"page":1,"x":308,"y":311,"width":255,"height":12}, commenced),
        'date_completed': map_box({"page":1,"x":310,"y":296,"width":255,"height":12}, completed),
        'final_tlv': map_box({"page":1,"x":313,"y":279,"width":246,"height":12}, job.final_tlv_reading),
        
        'sign_date': map_box({"page":1,"x":158,"y":150,"width":101,"height":12}, sign_date),
        'accreditation': map_box({"page":1,"x":401,"y":151,"width":170,"height":11}, job.accreditation_number, bold=True),
        'addtl_declaration': map_box({"page":1,"x":179,"y":67,"width":389,"height":79}, job.additional_declaration, max_lines=4),
    }

    enc = job.enclosure_type or ""
    pdf_checkbox_map = {
        'target_commodity':     {'is_checked': job.target_commodity, 'x': 50, 'y': 476},
        'target_container':     {'is_checked': job.target_container, 'x': 141, 'y': 476},
        'target_packing':       {'is_checked': job.target_packing, 'x': 236, 'y': 476},
        'target_other':         {'is_checked': bool(job.target_other), 'x': 46, 'y': 446},
        
        'enclosure_sheeted':    {'is_checked': "Sheeted" in enc, 'x': 324, 'y': 477},
        'enclosure_chamber':    {'is_checked': "Chamber" in enc, 'x': 405, 'y': 477},
        'enclosure_unsheeted':  {'is_checked': "Un-sheeted" in enc, 'x': 490, 'y': 477},
        'enclosure_other':      {'is_checked': "Other" in enc, 'x': 311, 'y': 444},
    }

    # ── Execute Drawing ──
    for key, data in pdf_data_map.items():
        draw_value(
            data.get('text'),
            data['x'],
            data['y'],
            bold=data.get('bold', False),
            font_size=data.get('font_size', 9),
            max_width=data.get('max_width'),
            max_lines=data.get('max_lines', 1),
            line_gap=data.get('line_gap', 11),
        )
            
    c.setFont("Helvetica-Bold", 10)
    for key, data in pdf_checkbox_map.items():
        if data.get('is_checked'):
            c.drawString(data['x'], data['y'], "X")
            
    c.save()
    buffer.seek(0)
    
    # ── Merge and Return ──
    text_layer = PdfReader(buffer)
    background = PdfReader(open(template_path, 'rb'))
    page = background.pages[0]
    page.merge_page(text_layer.pages[0])
    
    writer = PdfWriter()
    writer.add_page(page)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{job.certificate_number or job.id}.pdf"'
    writer.write(response)
    
    return response

@login_required
def inventory_report_view(request):
    """
    Inventory Usage Report to audit chemical consumption.
    """
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin account required.")
        return redirect('job_list')

    logs = InventoryUsageLog.objects.select_related('item', 'job__stock_warehouse', 'job__assigned_to').order_by('-created_at')

    item_id = request.GET.get('item_id', '')
    location_id = request.GET.get('location_id', '')
    worker_id = request.GET.get('worker_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if item_id:
        logs = logs.filter(item_id=item_id)
    if location_id:
        logs = logs.filter(job__stock_warehouse_id=location_id)
    if worker_id:
        logs = logs.filter(job__assigned_to_id=worker_id)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    items = InventoryItem.objects.all().order_by('name')
    locations = WarehouseLocation.objects.all().order_by('name')
    from django.contrib.auth.models import User
    workers = User.objects.filter(is_staff=False, is_superuser=False).order_by('first_name', 'username')

    context = {
        'logs': logs,
        'items': items,
        'locations': locations,
        'workers': workers,
        'item_id': item_id,
        'location_id': location_id,
        'worker_id': worker_id,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Inventory Usage Report',
    }
    return render(request, 'inventory_app/inventory_report.html', context)

@login_required
def job_json_data(request, job_id):
    """Returns JSON data of a job for copying fields."""
    job = get_object_or_404(Job, pk=job_id)
    data = {
        'container_number': job.container_number,
        'title': job.title,
        'chemical_item': job.chemical_item_id,
        'chemical_amount': str(job.chemical_amount) if job.chemical_amount else '',
        'chemical_unit': job.chemical_unit,
        'source_warehouse': job.source_warehouse_id,
        'execution_address': job.execution_address,
        'cha': job.cha_id,
        'exporter': job.exporter_id,
        'client': job.client_id,
        'cargo_description': job.cargo_description,
        'quantity_pkgs': job.quantity_pkgs,
        'site_location': job.site_location,
        'working_address': job.working_address,
        'subject': job.subject,
        'certificate_name': job.certificate_name,
        'is_third_party_vendor': job.is_third_party_vendor,
        'branch': job.branch,
        'customer_id_bill_to': job.customer_id_bill_to,
        'remarks': job.remarks,
        'task_description': job.task_description,
        'stock_warehouse': job.stock_warehouse_id,
        'other_supporting_work': job.other_supporting_work,
        'vessel_voyage': job.vessel_voyage,
        'port_of_loading': job.port_of_loading,
        'destination_country': job.destination_country,
        'commodity_country_of_origin': job.commodity_country_of_origin,
        'gross_weight': job.gross_weight,
        'net_weight': job.net_weight,
        'target_of_fumigation': job.target_of_fumigation,
        'enclosure_type': job.enclosure_type,
    }
    return JsonResponse(data)

@login_required
def worker_history_view(request):
    """View to show completed jobs for the field worker."""
    jobs = Job.objects.filter(assigned_workers=request.user, status='completed').order_by('-datetime_completed')
    return render(request, 'inventory_app/worker_history.html', {'jobs': jobs})
