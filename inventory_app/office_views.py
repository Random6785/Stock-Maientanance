"""
Office Portal Views
-------------------
All views here are restricted to users with is_staff=True.
Regular field workers are redirected to the login page.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.template.loader import get_template
from django.utils import timezone
from datetime import timedelta
import json
import io
import os
from django.conf import settings

try:
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
except ImportError:
    pass
from .models import InventoryItem, InventoryUsageLog, Job, WarehouseLocation, StockLevel, CHA, Exporter, Client
from .forms import JobAssignForm, JobForm, InventoryItemForm, WarehouseLocationForm, StockLevelForm, CHAForm, ExporterForm, FieldWorkerCreationForm


# ─────────────────────────────────────────────────────────────────────────────
# Access-control decorator
# ─────────────────────────────────────────────────────────────────────────────

def staff_required(view_func):
    """
    Ensures the user is both authenticated AND is_staff=True.
    Non-staff users are shown an error and redirected to their own job list.
    Unauthenticated users are redirected to the login page.
    """
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(
                request,
                "Access denied. This portal is restricted to office staff."
            )
            return redirect('job_list')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_dashboard(request):
    """
    Main landing page for office staff.
    Stat cards: pending jobs, completed jobs today, total inventory units.
    Recent activity: last 10 completed jobs.
    """
    today = timezone.localdate()

    # ── Stat card data ────────────────────────────────────────────────────────
    total_pending   = Job.objects.filter(status='pending').count()
    completed_today = Job.objects.filter(status='completed', updated_at__date=today).count()
    total_completed = Job.objects.filter(status='completed').count()

    total_inventory = StockLevel.objects.aggregate(
                          total=Sum('quantity')
                      )['total'] or 0

    # ── Recent activity table ─────────────────────────────────────────────────
    recent_jobs = (
        Job.objects
        .select_related('assigned_to')
        .filter(status='completed')
        .order_by('-execution_date', '-updated_at')[:10]
    )

    # ── Inventory at-a-glance (for the sidebar badge) ─────────────────────────
    low_stock_items = (
        InventoryItem.objects
        .annotate(total_stock_computed=Sum('stock_levels__quantity'))
        .filter(total_stock_computed__lte=5)
        .order_by('total_stock_computed')
    )
    low_stock_count = low_stock_items.count()
    job_status_data = json.dumps([total_completed, total_pending])

    # ── Chart Data: Chemicals Used (Last 7 Days) ──────────────────────────────
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    date_labels  = [d.strftime('%a') for d in last_7_days]

    start_date = timezone.now() - timedelta(days=7)
    logs = InventoryUsageLog.objects.filter(created_at__gte=start_date).select_related('item')

    from collections import defaultdict
    usage_by_item = defaultdict(lambda: defaultdict(int))
    total_by_item = defaultdict(int)

    for log in logs:
        d = log.created_at.astimezone().date()
        usage_by_item[log.item.name][d] += log.amount_used
        total_by_item[log.item.name]    += log.amount_used

    top_items = sorted(total_by_item.keys(), key=lambda k: total_by_item[k], reverse=True)[:3]

    chemicals_series = []
    for item_name in top_items:
        data = [float(usage_by_item[item_name].get(d, 0)) for d in last_7_days]
        chemicals_series.append({'name': item_name, 'data': data})

    chemicals_series_json = json.dumps(chemicals_series)
    date_labels_json      = json.dumps(date_labels)

    chemical_totals = [{'name': name, 'total': total} for name, total in sorted(total_by_item.items(), key=lambda x: x[1], reverse=True)]

    context = {
        'total_pending':    total_pending,
        'completed_today':  completed_today,
        'total_inventory':  total_inventory,
        'low_stock_count':  low_stock_count,
        'recent_jobs':      recent_jobs,
        'low_stock_items':  low_stock_items,
        'job_status_data':  job_status_data,
        'chemicals_series': chemicals_series_json,
        'date_labels':      date_labels_json,
        'chemical_totals':  chemical_totals,
        'page_title':       'Dashboard',
    }
    return render(request, 'office/office_dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Job Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_job_list(request):
    """All jobs with status filter support and advanced filtering."""
    status_filter  = request.GET.get('status', '')
    from_date      = request.GET.get('from_date', '')
    to_date        = request.GET.get('to_date', '')
    cert_no        = request.GET.get('cert_no', '')
    worker_id      = request.GET.get('worker', '')
    invoice_search = request.GET.get('invoice_search', '')
    exporter       = request.GET.get('exporter', '')
    buyer          = request.GET.get('buyer', '')
    cha            = request.GET.get('cha', '')
    country        = request.GET.get('country', '')
    accreditation  = request.GET.get('accreditation', '')

    from django.db.models import Q
    jobs = Job.objects.select_related('assigned_to').prefetch_related('assigned_workers', 'images').all()

    if status_filter in ('pending', 'completed'):
        jobs = jobs.filter(status=status_filter)

    if from_date:
        jobs = jobs.filter(execution_date__gte=from_date)
    if to_date:
        jobs = jobs.filter(execution_date__lte=to_date)
    if cert_no:
        jobs = jobs.filter(Q(certificate_number__icontains=cert_no) | Q(container_number__icontains=cert_no))
    if worker_id:
        jobs = jobs.filter(assigned_workers__id=worker_id)
    if invoice_search:
        jobs = jobs.filter(consignment_link__icontains=invoice_search)
    if exporter:
        jobs = jobs.filter(exporter__name__icontains=exporter)
    if buyer:
        jobs = jobs.filter(Q(client__name__icontains=buyer) | Q(customer_bill_to__icontains=buyer))
    if cha:
        jobs = jobs.filter(cha__name__icontains=cha)
    if country:
        jobs = jobs.filter(destination_country__icontains=country)
    if accreditation:
        jobs = jobs.filter(accreditation_number__icontains=accreditation)

    workers = User.objects.filter(is_staff=False, is_superuser=False).order_by('first_name', 'username')

    context = {
        'jobs':           jobs,
        'status_filter':  status_filter,
        'from_date':      from_date,
        'to_date':        to_date,
        'cert_no':        cert_no,
        'worker_id':      worker_id,
        'invoice_search': invoice_search,
        'exporter':       exporter,
        'buyer':          buyer,
        'cha':            cha,
        'country':        country,
        'accreditation':  accreditation,
        'workers':        workers,
        'page_title':     'All Jobs',
    }
    return render(request, 'office/office_job_list.html', context)


@staff_required
def office_job_create(request):
    """Create a new job using JobAssignForm. Redirects to job list on success."""
    if request.method == 'POST':
        form = JobAssignForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            
            # Handle Exporter creation/linking
            exp_name = form.cleaned_data.get('exporter_name')
            exp_phone = form.cleaned_data.get('exporter_phone')
            if exp_name:
                exporter, _ = Exporter.objects.get_or_create(name=exp_name, defaults={'mobile_number': exp_phone})
                job.exporter = exporter
                
            # Handle CHA creation/linking
            cha_name = form.cleaned_data.get('cha_name')
            cha_contact = form.cleaned_data.get('cha_contact_person')
            cha_phone = form.cleaned_data.get('cha_phone')
            if cha_name:
                cha, _ = CHA.objects.get_or_create(name=cha_name, defaults={'contact_person': cha_contact, 'mobile_number': cha_phone})
                job.cha = cha
                
            job.save()
            form.save_m2m() # Important for many-to-many fields like assigned_workers
            
            messages.success(
                request,
                f"Job #{job.pk} ({job.title or 'New Job'}) created and assigned successfully."
            )
            return redirect('office_job_list')
    else:
        form = JobAssignForm(initial={
            'scheduled_date': timezone.localdate(),
        })

    context = {
        'form':       form,
        'page_title': 'Assign New Job',
        'form_title': 'Create & Assign Job',
        'form_subtitle': 'Use the form below to quickly assign a new job to field workers.',
        'submit_label': 'Assign Job',
        'cancel_url': 'office_job_list',
    }
    return render(request, 'office/job_assign_form.html', context)


@staff_required
def office_job_edit(request, job_id):
    """Edit an existing job using a pre-filled ModelForm."""
    job = get_object_or_404(Job, pk=job_id)

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save(commit=False)
            job.save()
            form.save_m2m()  # Critical: saves assigned_workers ManyToMany data
            messages.success(
                request,
                f"Job #{job.pk} ({job.container_number}) updated successfully."
            )
            return redirect('office_job_list')
    else:
        form = JobForm(instance=job)

    context = {
        'form':         form,
        'job':          job,
        'page_title':   f'Edit Job #{job.pk}',
        'form_title':   f'Edit Job — {job.container_number}',
        'form_subtitle': f'Updating Job #{job.pk} · currently {job.get_status_display()}',
        'submit_label': 'Save Changes',
        'cancel_url': 'office_job_list',
        'is_edit': True,
    }
    return render(request, 'office/office_job_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PDF Coordinate Helper Function
# ─────────────────────────────────────────────────────────────────────────────

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


@staff_required
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
    # HOW TO USE map_box():
    # 1. Open your online PDF tool and measure a field
    # 2. Copy the dictionary it gives you: {"page":1,"x":219,"y":666,"width":96,"height":14}
    # 3. Paste it into map_box() like this:
    #    'field_name': map_box({"page":1,"x":219,"y":666,"width":96,"height":14}, job.field_value)
    
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

# ─────────────────────────────────────────────────────────────────────────────
# Inventory
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_inventory(request):
    """
    Multi-location inventory matrix view.

    Query strategy (2 DB hits total — zero N+1):
      1. Fetch all WarehouseLocation rows (ordered by name).
      2. Fetch all InventoryItem rows prefetching their StockLevel rows
         (with location) in a single JOIN query via prefetch_related.

    Then pivot in Python to build:
      matrix_rows  — list of dicts, one per item, with per-location quantities.
      location_totals — total units at each location (for the stat cards).
      grand_total  — sum of ALL stock across ALL items and ALL locations.
    """
    from .models import WarehouseLocation, StockLevel
    from django.db.models import Sum, Prefetch

    # ── 1. All locations (ordered) ────────────────────────────────────────────
    locations = list(WarehouseLocation.objects.all())            # query 1

    # ── 2. All items + their StockLevel rows in one prefetch ──────────────────
    items = list(
        InventoryItem.objects.prefetch_related(
            Prefetch(
                'stock_levels',
                queryset=StockLevel.objects.select_related('location'),
            )
        ).order_by('name')
    )                                                            # query 2

    # ── 3. Pivot in Python ────────────────────────────────────────────────────
    grand_total     = 0
    location_totals = {loc.id: 0 for loc in locations}   # {loc_id: qty}

    matrix_rows = []
    for item in items:
        # Build a lookup map for this item: {location_id: quantity}
        level_map = {sl.location_id: sl.quantity for sl in item.stock_levels.all()}

        row_total = sum(level_map.values())
        grand_total += row_total

        cells = []
        for loc in locations:
            qty = level_map.get(loc.id, 0)
            location_totals[loc.id] = location_totals.get(loc.id, 0) + qty
            cells.append(qty)

        matrix_rows.append({
            'item':      item,
            'total':     row_total,
            'cells':     cells,          # parallel list aligned to `locations`
        })

    # ── 4. Build location stat cards list ────────────────────────────────────
    location_stats = [
        {'location': loc, 'total': location_totals.get(loc.id, 0)}
        for loc in locations
    ]

    context = {
        'locations':       locations,
        'matrix_rows':     matrix_rows,
        'location_stats':  location_stats,
        'grand_total':     grand_total,
        'low_stock_count': sum(1 for row in matrix_rows if row['total'] <= 5),
        'page_title':      'Inventory',
    }
    return render(request, 'office/office_inventory.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Item Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_item_create(request):
    """Create a new InventoryItem."""
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save()
            from .models import WarehouseLocation, StockLevel
            for key, value in form.cleaned_data.items():
                if key.startswith('stock_location_') and value is not None:
                    loc_id = int(key.split('_')[-1])
                    loc = WarehouseLocation.objects.get(id=loc_id)
                    StockLevel.objects.update_or_create(
                        item=item,
                        location=loc,
                        defaults={'quantity': value}
                    )
            messages.success(request, f"Item '{item.name}' created successfully with stock levels.")
            return redirect('office_inventory')
    else:
        form = InventoryItemForm()

    context = {
        'form': form,
        'page_title': 'Add New Item',
        'form_title': 'Create Inventory Item',
        'form_subtitle': 'Add a new chemical or supply item directly to the portal.',
        'submit_label': 'Save Item',
        'cancel_url': 'office_inventory',
        'breadcrumb_parent_url': 'office_inventory',
        'breadcrumb_parent_label': 'Inventory',
    }
    return render(request, 'office/office_item_form.html', context)


@staff_required
def office_item_edit(request, item_id):
    """Edit an existing InventoryItem."""
    item = get_object_or_404(InventoryItem, pk=item_id)

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            from .models import WarehouseLocation, StockLevel
            for key, value in form.cleaned_data.items():
                if key.startswith('stock_location_') and value is not None:
                    loc_id = int(key.split('_')[-1])
                    loc = WarehouseLocation.objects.get(id=loc_id)
                    StockLevel.objects.update_or_create(
                        item=item,
                        location=loc,
                        defaults={'quantity': value}
                    )
            messages.success(request, f"Item '{item.name}' updated successfully.")
            return redirect('office_inventory')
    else:
        form = InventoryItemForm(instance=item)

    context = {
        'form': form,
        'page_title': f'Edit {item.name}',
        'form_title': f'Edit Item — {item.name}',
        'form_subtitle': 'Update existing inventory item details and stock levels.',
        'submit_label': 'Save Changes',
        'cancel_url': 'office_inventory',
        'is_edit': True,
        'breadcrumb_parent_url': 'office_inventory',
        'breadcrumb_parent_label': 'Inventory',
    }
    return render(request, 'office/office_item_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Warehouse Location Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_location_create(request):
    """Create a new WarehouseLocation."""
    if request.method == 'POST':
        form = WarehouseLocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Location '{loc.name}' created successfully.")
            return redirect('office_inventory')
    else:
        form = WarehouseLocationForm()

    context = {
        'form': form,
        'page_title': 'Add New Location',
        'form_title': 'Create Warehouse Location',
        'form_subtitle': 'Add a new storage facility.',
        'submit_label': 'Save Location',
        'cancel_url': 'office_inventory',
        'breadcrumb_parent_url': 'office_inventory',
        'breadcrumb_parent_label': 'Inventory',
    }
    return render(request, 'office/office_generic_form.html', context)


@staff_required
def office_location_edit(request, loc_id):
    """Edit an existing WarehouseLocation."""
    loc = get_object_or_404(WarehouseLocation, pk=loc_id)

    if request.method == 'POST':
        form = WarehouseLocationForm(request.POST, instance=loc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Location '{loc.name}' updated successfully.")
            return redirect('office_inventory')
    else:
        form = WarehouseLocationForm(instance=loc)

    context = {
        'form': form,
        'page_title': f'Edit {loc.name}',
        'form_title': f'Edit Location — {loc.name}',
        'form_subtitle': 'Update warehouse facility details.',
        'submit_label': 'Save Changes',
        'cancel_url': 'office_inventory',
        'is_edit': True,
        'breadcrumb_parent_url': 'office_inventory',
        'breadcrumb_parent_label': 'Inventory',
    }
    return render(request, 'office/office_generic_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Stock Level Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_stock_list(request):
    """Location-grouped stock levels. Handles inline F-expression stock additions."""
    if request.method == 'POST' and request.POST.get('action') == 'add_stock':
        from django.db.models import F
        from decimal import Decimal, InvalidOperation

        updated_count = 0
        for key, raw_value in request.POST.items():
            if not key.startswith('add_stock_to_'):
                continue
            raw_value = raw_value.strip()
            if not raw_value:
                continue
            try:
                added = Decimal(raw_value)
            except InvalidOperation:
                continue
            if added <= 0:
                continue

            stock_pk = key.replace('add_stock_to_', '')
            try:
                stock_pk = int(stock_pk)
            except ValueError:
                continue

            # Atomic F-expression increment — race-condition safe
            rows = StockLevel.objects.filter(pk=stock_pk).update(
                quantity=F('quantity') + added
            )
            if rows:
                updated_count += 1

        if updated_count:
            messages.success(request, f"Stock updated for {updated_count} item(s) successfully.")
        else:
            messages.warning(request, "No stock additions were made — all fields were empty or zero.")
        return redirect('office_stock_list')

    # ── Build location-grouped data for the template ───────────────────────────
    locations = WarehouseLocation.objects.order_by('name')
    stocks_qs = (
        StockLevel.objects
        .select_related('item', 'location')
        .order_by('location__name', 'item__name')
    )

    # Group: { location_obj: [stock1, stock2, ...] }
    from collections import OrderedDict
    grouped = OrderedDict()
    for loc in locations:
        grouped[loc] = []

    for stock in stocks_qs:
        if stock.location in grouped:
            grouped[stock.location].append(stock)

    # Build a flat list of (location, stocks_list, total_qty) tuples for the template
    location_groups = [
        {
            'location': loc,
            'stocks':   stock_list,
            'total':    sum(s.quantity for s in stock_list),
        }
        for loc, stock_list in grouped.items()
    ]

    context = {
        'location_groups': location_groups,
        'page_title':      'Manage Stock Levels',
    }
    return render(request, 'office/office_stock_list.html', context)


@staff_required
@never_cache
def office_stock_create(request):
    """Create a new StockLevel."""
    if request.method == 'POST':
        form = StockLevelForm(request.POST)
        if form.is_valid():
            sl = form.save()
            messages.success(request, f"Stock level for '{sl.item.name}' at '{sl.location.name}' created.")
            return redirect('office_stock_list')
    else:
        # If passed via GET ?item= & location=
        initial_data = {}
        if 'item' in request.GET:
            initial_data['item'] = request.GET['item']
        if 'location' in request.GET:
            initial_data['location'] = request.GET['location']
        form = StockLevelForm(initial=initial_data)

    context = {
        'form': form,
        'page_title': 'Add Stock Entry',
        'form_title': 'Create Stock Entry',
        'form_subtitle': 'Record new stock quantity for a warehouse location.',
        'submit_label': 'Save Entry',
        'cancel_url': 'office_stock_list',
        'breadcrumb_parent_url': 'office_stock_list',
        'breadcrumb_parent_label': 'Stock Levels',
    }
    return render(request, 'office/office_generic_form.html', context)


@staff_required
@never_cache
def office_stock_edit(request, stock_id):
    """Edit an existing StockLevel."""
    stock = get_object_or_404(StockLevel, pk=stock_id)

    if request.method == 'POST':
        form = StockLevelForm(request.POST, instance=stock)
        if form.is_valid():
            sl = form.save()
            messages.success(request, f"Stock level for '{sl.item.name}' at '{sl.location.name}' updated.")
            return redirect('office_stock_list')
    else:
        form = StockLevelForm(instance=stock)

    context = {
        'form': form,
        'page_title': f'Edit Stock',
        'form_title': f'Edit Stock — {stock.item.name}',
        'form_subtitle': f'Updating stock for {stock.location.name}.',
        'submit_label': 'Save Changes',
        'cancel_url': 'office_stock_list',
        'is_edit': True,
        'breadcrumb_parent_url': 'office_stock_list',
        'breadcrumb_parent_label': 'Stock Levels',
    }
    return render(request, 'office/office_generic_form.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Quick Edit JSON APIs (Logistics / Parties)
# ─────────────────────────────────────────────────────────────────────────────
import json

@staff_required
def api_cha_detail(request, pk):
    """Return JSON details of a CHA."""
    cha = get_object_or_404(CHA, pk=pk)
    return JsonResponse({
        'id': cha.id,
        'name': cha.name,
        'address': cha.address or '',
        'contact_person': cha.contact_person or '',
        'mobile_number': cha.mobile_number or '',
    })

@staff_required
def api_cha_save(request):
    """Save (Create or Edit) a CHA via AJAX."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cha_id = data.get('id')
            if cha_id:
                cha = get_object_or_404(CHA, pk=cha_id)
                form = CHAForm(data, instance=cha)
            else:
                form = CHAForm(data)
            
            if form.is_valid():
                cha = form.save()
                return JsonResponse({'success': True, 'id': cha.id, 'name': cha.name})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
        except Exception as e:
            return JsonResponse({'success': False, 'errors': str(e)})
    return JsonResponse({'success': False, 'errors': 'Invalid request method'})


@staff_required
def api_exporter_detail(request, pk):
    """Return JSON details of an Exporter."""
    exporter = get_object_or_404(Exporter, pk=pk)
    return JsonResponse({
        'id': exporter.id,
        'name': exporter.name,
        'address': exporter.address or '',
        'contact_person': exporter.contact_person or '',
        'mobile_number': exporter.mobile_number or '',
    })

@staff_required
def api_exporter_save(request):
    """Save (Create or Edit) an Exporter via AJAX."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            exporter_id = data.get('id')
            if exporter_id:
                exporter = get_object_or_404(Exporter, pk=exporter_id)
                form = ExporterForm(data, instance=exporter)
            else:
                form = ExporterForm(data)
            
            if form.is_valid():
                exporter = form.save()
                return JsonResponse({'success': True, 'id': exporter.id, 'name': exporter.name})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
        except Exception as e:
            return JsonResponse({'success': False, 'errors': str(e)})
    return JsonResponse({'success': False, 'errors': 'Invalid request method'})

@staff_required
def api_create_client(request):
    """Save (Create) a Client via AJAX."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Create a new Client directly
            client = Client.objects.create(
                name=data.get('name'),
                address=data.get('address', ''),
                city=data.get('city', ''),
                country=data.get('country', ''),
            )
            return JsonResponse({'success': True, 'id': client.id, 'name': client.name})
        except Exception as e:
            return JsonResponse({'success': False, 'errors': str(e)})
    return JsonResponse({'success': False, 'errors': 'Invalid request method'})

@staff_required
def api_get_job_data(request, pk):
    job = get_object_or_404(Job, pk=pk)
    data = {
        'container_number': job.container_number,
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
    return JsonResponse({'success': True, 'data': data})

# ─────────────────────────────────────────────────────────────────────────────
# Field Worker Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
def office_worker_list(request):
    """List all Field Workers (non-staff users)."""
    workers = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    context = {
        'workers': workers,
        'page_title': 'Field Workers',
    }
    return render(request, 'office/office_worker_list.html', context)


@staff_required
def office_worker_create(request):
    """Provision a new Field Worker account."""
    if request.method == 'POST':
        form = FieldWorkerCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = False
            user.is_superuser = False
            user.save()
            messages.success(request, f"Field Worker '{user.username}' provisioned successfully.")
            return redirect('office_worker_list')
    else:
        form = FieldWorkerCreationForm()

    context = {
        'form': form,
        'page_title': 'Provision Field Worker',
    }
    return render(request, 'office/office_worker_form.html', context)

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Analytics & Incremental Stock Management
# ─────────────────────────────────────────────────────────────────────────────

@staff_required
@never_cache
def office_add_stock(request):
    """Increment stock for a specific item at a specific location."""
    if request.method == 'POST':
        item_id = request.POST.get('item')
        location_id = request.POST.get('location')
        amount = request.POST.get('amount')
        
        if not all([item_id, location_id, amount]):
            messages.error(request, "Please fill in all fields.")
            return redirect('office_add_stock')
            
        try:
            amount_val = int(amount)
            if amount_val <= 0:
                messages.error(request, "Amount must be greater than 0.")
                return redirect('office_add_stock')
                
            from django.db.models import F
            
            sl, created = StockLevel.objects.get_or_create(
                item_id=item_id, 
                location_id=location_id,
                defaults={'quantity': 0}
            )
            
            if not created:
                StockLevel.objects.filter(id=sl.id).update(quantity=F('quantity') + amount_val)
            else:
                sl.quantity = amount_val
                sl.save()
            
            item = InventoryItem.objects.get(id=item_id)
            loc = WarehouseLocation.objects.get(id=location_id)
            messages.success(request, f"Successfully added {amount_val} units to '{item.name}' at '{loc.name}'.")
            return redirect('office_inventory')
            
        except ValueError:
            messages.error(request, "Invalid amount.")
            return redirect('office_add_stock')

    items = InventoryItem.objects.all().order_by('name')
    locations = WarehouseLocation.objects.all().order_by('name')
    
    context = {
        'items': items,
        'locations': locations,
        'page_title': 'Add Stock',
        'form_title': 'Add Stock Incrementally',
        'form_subtitle': 'Select an item, location and add quantity.',
        'submit_label': 'Add Stock',
        'cancel_url': 'office_inventory',
        'breadcrumb_parent_url': 'office_inventory',
        'breadcrumb_parent_label': 'Inventory',
    }
    return render(request, 'office/office_add_stock.html', context)


@staff_required
def office_usage_history(request):
    """Usage Analytics Report"""
    item_filter = request.GET.get('item', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    location_filter = request.GET.get('location', '')
    
    logs = InventoryUsageLog.objects.select_related('item', 'job__stock_warehouse', 'job__assigned_to').all()
    
    if item_filter:
        logs = logs.filter(item_id=item_filter)
    if from_date:
        logs = logs.filter(created_at__date__gte=from_date)
    if to_date:
        logs = logs.filter(created_at__date__lte=to_date)
    if location_filter:
        logs = logs.filter(job__stock_warehouse_id=location_filter)
        
    items = InventoryItem.objects.all().order_by('name')
    locations = WarehouseLocation.objects.all().order_by('name')
    
    context = {
        'logs': logs,
        'items': items,
        'locations': locations,
        'item_filter': item_filter,
        'from_date': from_date,
        'to_date': to_date,
        'location_filter': location_filter,
        'page_title': 'Inventory Usage History',
    }
    return render(request, 'office/office_usage_history.html', context)
