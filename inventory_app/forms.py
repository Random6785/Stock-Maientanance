from django import forms
from django.forms import modelformset_factory
from .models import InventoryUsageLog, Job, InventoryItem, WarehouseLocation, StockLevel, CHA, Exporter, Client
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


# ─────────────────────────────────────────────────────────────────────────────
# Job Form — used by the Office Portal Create & Edit views
# ─────────────────────────────────────────────────────────────────────────────

class JobForm(forms.ModelForm):
    """
    ModelForm for Job with Bootstrap 5 widgets applied to every field.
    Used for both creating and editing jobs in the Office Portal.
    """

    class Meta:
        model = Job
        fields = [
            'title',
            'container_number',
            'status',
            'scheduled_date',
            'execution_date',
            'notes',
            'cha',
            'exporter',
            'cargo_description',
            'quantity_pkgs',
            'site_location',
            'working_address',
            'subject',
            'certificate_name',
            'is_third_party_vendor',
            'branch',
            'customer_id_bill_to',
            'remarks',
            'task_description',
            'stock_warehouse',
            'other_supporting_work',
            'chemical_item',
            'chemical_amount',
            'chemical_unit',
            'source_warehouse',
            'execution_address',
            'client',
            'vessel_voyage',
            'port_of_loading',
            'dosage',
            'method_application',
            'stack_size',
            'issue_date',
            'fumigation_date',
            'expiry_date',
            'destination_country',
            'consignment_link',
            'commodity_country_of_origin',
            'gross_weight',
            'net_weight',
            'target_of_fumigation',
            'enclosure_type',
            'datetime_commenced',
            'datetime_completed',
            'final_tlv_reading',
            'certificate_number',
            'customer_bill_to',
            'name_of_fumigant',
            'place_of_fumigation_general',
            'container_type_description',
            'total_containers',
            'print_container_size',
            'seal_numbers',
            'commodity_description',
            'net_weight_unit',
            'gross_weight_unit',
            'target_commodity',
            'target_container',
            'target_packing',
            'target_other',
            'prescribed_dose',
            'prescribed_exposure',
            'prescribed_temp',
            'applied_dose',
            'applied_exposure',
            'applied_temp',
            'fumigation_street',
            'fumigation_city',
            'fumigation_country',
            'fumigation_postcode',
            'operator_name',
            'certificate_sign_date',
            'additional_declaration',
            'treatment_provider_id',
            'accreditation_number',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Mundra Fumigation'
            }),
            'container_number': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'e.g. CONT-2026-001',
                'autocomplete': 'off',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
            'execution_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  3,
                'placeholder': 'Optional instructions or notes for the field worker…',
            }),
            'cha': forms.Select(attrs={
                'class': 'form-select',
            }),
            'exporter': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cargo_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'quantity_pkgs': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'site_location': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'working_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'certificate_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'is_third_party_vendor': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'branch': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'customer_id_bill_to': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'task_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'stock_warehouse': forms.Select(attrs={
                'class': 'form-select',
            }),
            'chemical_item': forms.Select(attrs={
                'class': 'form-select',
            }),
            'chemical_amount': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            'chemical_unit': forms.Select(attrs={
                'class': 'form-select',
            }),
            'source_warehouse': forms.Select(attrs={
                'class': 'form-select',
            }),
            'execution_address': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'other_supporting_work': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'vessel_voyage': forms.TextInput(attrs={'class': 'form-control'}),
            'port_of_loading': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'method_application': forms.TextInput(attrs={'class': 'form-control'}),
            'stack_size': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fumigation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'destination_country': forms.TextInput(attrs={'class': 'form-control'}),
            'consignment_link': forms.TextInput(attrs={'class': 'form-control'}),
            'commodity_country_of_origin': forms.TextInput(attrs={'class': 'form-control'}),
            'gross_weight': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2000 KGS'}),
            'net_weight': forms.TextInput(attrs={'class': 'form-control'}),
            'target_of_fumigation': forms.Select(attrs={'class': 'form-select'}),
            'enclosure_type': forms.Select(attrs={'class': 'form-select'}),
            'datetime_commenced': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'datetime_completed': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'final_tlv_reading': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_bill_to': forms.TextInput(attrs={'class': 'form-control'}),
            'name_of_fumigant': forms.TextInput(attrs={'class': 'form-control'}),
            'place_of_fumigation_general': forms.TextInput(attrs={'class': 'form-control'}),
            'container_type_description': forms.TextInput(attrs={'class': 'form-control'}),
            'total_containers': forms.NumberInput(attrs={'class': 'form-control'}),
            'print_container_size': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'seal_numbers': forms.TextInput(attrs={'class': 'form-control'}),
            'commodity_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'net_weight_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'gross_weight_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'target_commodity': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_container': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_packing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_other': forms.TextInput(attrs={'class': 'form-control'}),
            'prescribed_dose': forms.TextInput(attrs={'class': 'form-control'}),
            'prescribed_exposure': forms.TextInput(attrs={'class': 'form-control'}),
            'prescribed_temp': forms.TextInput(attrs={'class': 'form-control'}),
            'applied_dose': forms.TextInput(attrs={'class': 'form-control'}),
            'applied_exposure': forms.TextInput(attrs={'class': 'form-control'}),
            'applied_temp': forms.TextInput(attrs={'class': 'form-control'}),
            'fumigation_street': forms.TextInput(attrs={'class': 'form-control'}),
            'fumigation_city': forms.TextInput(attrs={'class': 'form-control'}),
            'fumigation_country': forms.TextInput(attrs={'class': 'form-control'}),
            'fumigation_postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'operator_name': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_sign_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'additional_declaration': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'treatment_provider_id': forms.TextInput(attrs={'class': 'form-control'}),
            'accreditation_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Job Title',
            'container_number': 'Container Number',
            'status':           'Job Status',
            'scheduled_date':   'Scheduled Date',
            'execution_date':   'Execution Date',
            'notes':            'Admin Notes',
            'cha':              'CHA',
            'exporter':         'Exporter',
            'cargo_description': 'Cargo Description',
            'quantity_pkgs':    'Quantity & Pkgs',
            'site_location':    'Site / Work Location',
            'working_address':  'Working Address',
            'subject':          'Subject',
            'certificate_name': 'Certificate Name',
            'is_third_party_vendor': 'Third Party Vendor',
            'branch': 'Branch',
            'customer_id_bill_to': 'Customer ID (Bill To)',
            'remarks': 'Remarks',
            'task_description': 'Task Description',
            'stock_warehouse': 'Stock Warehouse',
            'chemical_item': 'Chemical Item',
            'chemical_amount': 'Chemical Amount',
            'chemical_unit': 'Chemical Unit',
            'source_warehouse': 'Source Warehouse',
            'execution_address': 'Execution Address',
            'other_supporting_work': 'Other Supporting Work',
            'client': 'Client / Consignee',
            'vessel_voyage': 'Vessel / Voyage',
            'port_of_loading': 'Port of Loading',
            'dosage': 'Dosage',
            'method_application': 'Method of Application',
            'stack_size': 'Stack Size',
            'issue_date': 'Date of Issue',
            'fumigation_date': 'Date of Fumigation',
            'expiry_date': 'Expiry Date',
            'destination_country': 'Destination Country',
            'consignment_link': 'Consignment Link',
            'commodity_country_of_origin': 'Commodity Country of Origin',
            'gross_weight': 'Gross Weight (KGS)',
            'net_weight': 'Net Weight',
            'target_of_fumigation': 'Target of Fumigation',
            'enclosure_type': 'Enclosure Type',
            'datetime_commenced': 'Date/Time Commenced',
            'datetime_completed': 'Date/Time Completed',
            'final_tlv_reading': 'Final TLV Reading',
            'certificate_number': 'Certificate Number',
            'customer_bill_to': 'Customer Bill To',
            'name_of_fumigant': 'Name of Fumigant',
            'place_of_fumigation_general': 'Place of Fumigation (General)',
            'container_type_description': 'Container Type Description',
            'total_containers': 'Total Containers',
            'print_container_size': 'Print Container Size',
            'seal_numbers': 'Seal Numbers',
            'commodity_description': 'Commodity Description',
            'net_weight_unit': 'Net Weight Unit',
            'gross_weight_unit': 'Gross Weight Unit',
            'target_commodity': 'Target: Commodity',
            'target_container': 'Target: Container',
            'target_packing': 'Target: Packing',
            'target_other': 'Target: Other',
            'prescribed_dose': 'Prescribed Dose',
            'prescribed_exposure': 'Prescribed Exposure',
            'prescribed_temp': 'Prescribed Temp',
            'applied_dose': 'Applied Dose',
            'applied_exposure': 'Applied Exposure',
            'applied_temp': 'Applied Temp',
            'fumigation_street': 'Fumigation Street',
            'fumigation_city': 'Fumigation City',
            'fumigation_country': 'Fumigation Country',
            'fumigation_postcode': 'Fumigation Postcode',
            'operator_name': 'Operator Name',
            'certificate_sign_date': 'Certificate Sign Date',
            'additional_declaration': 'Additional Declaration',
            'treatment_provider_id': 'Treatment Provider ID',
            'accreditation_number': 'Accreditation Number',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Relax Form Validation: make all fields optional by default
        for field in self.fields:
            self.fields[field].required = False
            
        # Ensure only these are strictly required for creation
        strict_required_fields = [
            'title', 
            'container_number',
            'certificate_number',
            'treatment_provider_id',
            'customer_bill_to',
            'accreditation_number',
            'name_of_fumigant',
            'container_type_description',
            'operator_name'
        ]
        for field in strict_required_fields:
            if field in self.fields:
                self.fields[field].required = True

class JobAssignForm(forms.ModelForm):
    """
    Ultra-lean form for assigning jobs.
    Uses 'task_description' as 'chemical_instructions', 'is_third_party_vendor' as 'is_third_party',
    and 'site_location' as 'third_party_location'.
    """
    exporter_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Exporter Name'}))
    exporter_phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Exporter Phone'}))
    
    cha_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CHA Name'}))
    cha_contact_person = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person'}))
    cha_phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CHA Phone'}))

    class Meta:
        model = Job
        fields = [
            'task_description', # mapped to chemical_instructions
            'stock_warehouse',
            'execution_address',
            'title',
            'scheduled_date',
            'is_third_party_vendor', # mapped to is_third_party
            'site_location', # mapped to third_party_location
            'assigned_workers',
        ]
        widgets = {
            'assigned_workers': forms.CheckboxSelectMultiple(attrs={'class': 'btn-check'}),
            'task_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g., 2 Liters of chemical X...'}),
            'stock_warehouse': forms.Select(attrs={'class': 'form-select d-inline-block w-auto'}),
            'execution_address': forms.TextInput(attrs={'class': 'form-control d-inline-block w-auto', 'placeholder': 'address'}),
            'title': forms.TextInput(attrs={'class': 'form-control d-inline-block w-auto', 'placeholder': 'e.g., Job name'}),
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control d-inline-block w-auto', 'type': 'date'}),
            'is_third_party_vendor': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_third_party'}),
            'site_location': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_third_party_location', 'placeholder': 'Third Party Location'}),
        }
        labels = {
            'task_description': 'Chemical Instructions',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clear the default "New Job" value so the placeholder shows instead
        self.initial['title'] = ''
        
        self.fields['task_description'].required = True
        self.fields['assigned_workers'].required = True
        self.fields['scheduled_date'].required = True
        
        if 'assigned_workers' in self.fields:
            self.fields['assigned_workers'].queryset = (
                User.objects.filter(is_active=True, is_staff=False)
                            .order_by('first_name', 'username')
            )
            self.fields['assigned_workers'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}".strip() or obj.username


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Usage Log Form — used by the Field Worker job_detail view
# ─────────────────────────────────────────────────────────────────────────────

class InventoryUsageLogForm(forms.ModelForm):
    """
    Dynamic form for logging individual chemical/item usage on a job.
    No warehouse location here—that's selected at the job level.
    This form is used in a modelformset to allow multiple items per job.
    Supports decimal quantities (e.g. 0.4 L of HCL).
    """

    # Override to accept decimals
    amount_taken = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control amount-taken',
            'min': '0',
            'step': '0.001',
            'placeholder': '0.000',
            'data-role': 'amount-taken',
        })
    )
    amount_used = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control amount-used',
            'min': '0',
            'step': '0.001',
            'placeholder': '0.000',
            'data-role': 'amount-used',
        })
    )
    amount_returned = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=3,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control amount-returned',
            'min': '0',
            'step': '0.001',
            'placeholder': '0.000',
            'readonly': 'readonly',
            'data-role': 'amount-returned',
        })
    )

    class Meta:
        model = InventoryUsageLog
        fields = ['item', 'amount_taken', 'amount_used', 'amount_returned']
        widgets = {
            'item': forms.Select(attrs={
                'class': 'form-select item-select',
                'data-role': 'item-select',
            }),
        }
        labels = {
            'item': 'Chemical / Item',
            'amount_taken': 'Taken',
            'amount_used': 'Used',
            'amount_returned': 'Returned',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount_returned'].widget.attrs['readonly'] = True
        self.fields['amount_returned'].required = False

    def clean(self):
        cleaned_data = super().clean()
        taken = cleaned_data.get('amount_taken')
        used  = cleaned_data.get('amount_used')
        if taken is not None and used is not None:
            if used > taken:
                self.add_error('amount_used', 'Used cannot exceed Taken.')
            else:
                # Auto-calculate returned if not provided
                from decimal import Decimal
                cleaned_data['amount_returned'] = (taken - used).quantize(Decimal('0.001'))
        return cleaned_data


# Create modelformset — extra=0 because JS manages how many cards are shown;
# can_delete=True so the server can ignore empty/deleted forms.
InventoryUsageLogFormSet = modelformset_factory(
    InventoryUsageLog,
    form=InventoryUsageLogForm,
    extra=0,       # JS adds cards dynamically; don't pre-render Django extras
    can_delete=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Inventory & Locations Forms — used by the Office Portal
# ─────────────────────────────────────────────────────────────────────────────

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'description', 'image', 'unit_of_measurement']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Bifenthrin 25% EC'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'unit_of_measurement': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'name': 'Chemical / Item Name',
            'description': 'Description',
            'image': 'Item Image',
            'unit_of_measurement': 'Unit of Measurement',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import WarehouseLocation, StockLevel
        self.locations = WarehouseLocation.objects.all()
        for loc in self.locations:
            field_name = f'stock_location_{loc.id}'
            initial_stock = 0
            if self.instance and self.instance.pk:
                sl = StockLevel.objects.filter(item=self.instance, location=loc).first()
                if sl:
                    initial_stock = sl.quantity
            self.fields[field_name] = forms.IntegerField(
                initial=initial_stock,
                min_value=0,
                required=False,
                label=f"Stock at {loc.name}",
                widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
            )

class WarehouseLocationForm(forms.ModelForm):
    class Meta:
        model = WarehouseLocation
        fields = ['name', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Main Warehouse'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 123 Storage St'
            }),
        }
        labels = {
            'name': 'Location Name',
            'address': 'Location Address',
        }

class StockLevelForm(forms.ModelForm):
    class Meta:
        model = StockLevel
        fields = ['item', 'location', 'quantity']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
        labels = {
            'item': 'Inventory Item',
            'location': 'Warehouse Location',
            'quantity': 'Current Stock Quantity',
        }


# ─────────────────────────────────────────────────────────────────────────────
# Logistics / Parties Forms
# ─────────────────────────────────────────────────────────────────────────────

class CHAForm(forms.ModelForm):
    class Meta:
        model = CHA
        fields = ['name', 'address', 'city', 'country', 'contact_person', 'mobile_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ExporterForm(forms.ModelForm):
    class Meta:
        model = Exporter
        fields = ['name', 'address', 'city', 'country', 'contact_person', 'mobile_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'address', 'city', 'country', 'contact_person', 'mobile_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Field Worker Account Provisioning Form
# ─────────────────────────────────────────────────────────────────────────────

class FieldWorkerCreationForm(UserCreationForm):
    """
    Form for Office Admins to provision new Field Worker accounts.
    Overrides UserCreationForm to apply Bootstrap 5 styling to all fields.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply standard Bootstrap 5 form-control classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

