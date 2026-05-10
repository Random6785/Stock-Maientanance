from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

UNIT_CHOICES = (
    ('Liters', 'Liters'),
    ('Milliliters', 'Milliliters'),
    ('Kilograms', 'Kilograms'),
    ('Grams', 'Grams'),
    ('Units', 'Units'),
    ('Pieces', 'Pieces'),
)

class InventoryItem(models.Model):
    """Master list of inventory items (chemicals, bottles, supplies)."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='inventory_images/', 
        blank=True, 
        null=True, 
        help_text="Optional image of the chemical/item."
    )
    unit_of_measurement = models.CharField(
        max_length=50,
        choices=UNIT_CHOICES,
        default='Units',
        help_text="Unit of measurement for this item."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.unit_of_measurement})"

    class Meta:
        ordering = ['name']
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"


class WarehouseLocation(models.Model):
    """A physical warehouse / storage facility."""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Location name, e.g. 'Mundra', 'Ahmedabad'."
    )
    address = models.CharField(
        max_length=300,
        blank=True,
        help_text="Full street address or landmark."
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Warehouse Location"
        verbose_name_plural = "Warehouse Locations"


class StockLevel(models.Model):
    """
    Per-location quantity for an inventory item.
    Each row answers: "How many units of <item> are at <location>?"
    """
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='stock_levels'
    )
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.CASCADE,
        related_name='stock_levels'
    )
    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Units currently stored at this location."
    )

    def __str__(self):
        return f"{self.item.name} @ {self.location.name}: {self.quantity}"

    class Meta:
        unique_together = ('item', 'location')
        ordering = ['item__name', 'location__name']
        verbose_name = "Stock Level"
        verbose_name_plural = "Stock Levels"


class CHA(models.Model):
    """Customs House Agent (CHA) details for customs clearance purposes."""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    contact_person = models.CharField(max_length=150, blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "CHA"
        verbose_name_plural = "CHAs"


class Exporter(models.Model):
    """Exporter details for a shipment/job."""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    contact_person = models.CharField(max_length=150, blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Exporter"
        verbose_name_plural = "Exporters"


class Client(models.Model):
    """Consignee / Client details for a shipment/job."""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    contact_person = models.CharField(max_length=150, blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Job(models.Model):
    """A container cleaning job assigned to a field worker."""

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    )

    TARGET_CHOICES = (
        ('Commodity', 'Commodity'),
        ('Container', 'Container'),
        ('Packing', 'Packing'),
        ('Other', 'Other'),
    )

    ENCLOSURE_CHOICES = (
        ('Sheeted', 'Sheeted'),
        ('Chamber', 'Chamber'),
        ('Un-sheeted', 'Un-sheeted'),
        ('Other', 'Other'),
    )

    container_number = models.CharField(
        max_length=100,
        help_text="Identifier for the shipping container."
    )
    title = models.CharField(max_length=200, default="New Job", help_text="e.g., Mundra Fumigation")
    assigned_workers = models.ManyToManyField(User, related_name='assigned_jobs_multi', help_text="Workers assigned to this job.")
    
    # 'assigned_to' kept for migration backwards compatibility. Made nullable.
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_jobs',
        null=True,
        blank=True,
        help_text="[Deprecated] Field worker assigned to this job."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # scheduled_date: the *planned* date for the job.
    scheduled_date = models.DateField(
        help_text="The date the job is/was scheduled."
    )

    # execution_date: the *actual* date the job was performed.
    # NOT auto_now_add so admins can backdate it freely.
    execution_date = models.DateField(
        default=timezone.localdate,
        help_text=(
            "The actual date the job was executed. "
            "Admins can backdate this for retroactive data entry."
        )
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Admin notes or special instructions for this job."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1: Pre-execution Assignment Fields
    # ─────────────────────────────────────────────────────────────────────────
    chemical_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='assigned_jobs',
        help_text="Chemical to be used for this job."
    )
    chemical_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        blank=True, 
        null=True,
        help_text="Amount of chemical to take."
    )
    chemical_unit = models.CharField(
        max_length=50,
        choices=UNIT_CHOICES,
        blank=True,
        null=True,
        help_text="Unit for the chemical amount."
    )
    source_warehouse = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='assigned_jobs_source',
        help_text="Warehouse to take the chemical from."
    )
    execution_address = models.TextField(
        blank=True,
        null=True,
        help_text="Address where the job will be executed."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # New Office/Logistics Fields
    # ─────────────────────────────────────────────────────────────────────────
    cha = models.ForeignKey(
        CHA,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='jobs',
        help_text="Customs House Agent handling this job."
    )
    exporter = models.ForeignKey(
        Exporter,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='jobs',
        help_text="Exporter for this shipment."
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='jobs',
        help_text="Consignee / Client for this shipment."
    )
    cargo_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the cargo."
    )
    quantity_pkgs = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Quantity and packaging type (e.g., '100 Bags')."
    )
    site_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Specific site location for the job."
    )
    working_address = models.TextField(
        blank=True,
        null=True,
        help_text="Full working address."
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Subject line for reports/certificates."
    )
    certificate_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name to appear on certificates."
    )
    is_third_party_vendor = models.BooleanField(
        default=False,
        help_text="Indicates if a third-party vendor is executing the job."
    )
    branch = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Branch name."
    )
    customer_id_bill_to = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Customer ID (Bill To)."
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Optional remarks."
    )
    task_description = models.TextField(
        blank=True,
        null=True,
        help_text="Task description."
    )
    stock_warehouse = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='jobs',
        help_text="Warehouse location for stock deduction."
    )
    other_supporting_work = models.TextField(
        blank=True,
        null=True,
        help_text="Other supporting work details."
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2: PDF Certificate Fields
    # ─────────────────────────────────────────────────────────────────────────
    vessel_voyage = models.CharField(max_length=200, blank=True, null=True)
    port_of_loading = models.CharField(max_length=200, blank=True, null=True)
    destination_country = models.CharField(max_length=200, blank=True, null=True)
    consignment_link = models.CharField(max_length=500, blank=True, null=True)
    commodity_country_of_origin = models.CharField(max_length=200, blank=True, null=True)
    gross_weight = models.CharField(max_length=100, blank=True, null=True, help_text="Include 'KGS'")
    net_weight = models.CharField(max_length=100, blank=True, null=True)
    
    target_of_fumigation = models.CharField(max_length=50, choices=TARGET_CHOICES, blank=True, null=True)
    enclosure_type = models.CharField(max_length=50, choices=ENCLOSURE_CHOICES, blank=True, null=True)

    datetime_commenced = models.DateTimeField(blank=True, null=True)
    datetime_completed = models.DateTimeField(blank=True, null=True)
    final_tlv_reading = models.CharField(max_length=100, blank=True, null=True)

    dosage = models.CharField(max_length=200, blank=True, null=True)
    method_application = models.CharField(max_length=200, blank=True, null=True)
    stack_size = models.CharField(max_length=200, blank=True, null=True)
    
    issue_date = models.DateField(blank=True, null=True, help_text="Date of Issue")
    fumigation_date = models.DateField(blank=True, null=True, help_text="Date of Fumigation")
    expiry_date = models.DateField(blank=True, null=True, help_text="Expiry Date")

    # --- Phase 1: Exhaustive Data Schema New Fields ---
    certificate_number = models.CharField(max_length=200, blank=True, null=True)
    customer_bill_to = models.CharField(max_length=200, blank=True, null=True)
    name_of_fumigant = models.CharField(max_length=200, blank=True, null=True)
    place_of_fumigation_general = models.CharField(max_length=200, blank=True, null=True)
    container_type_description = models.CharField(max_length=200, blank=True, null=True)
    total_containers = models.IntegerField(blank=True, null=True)
    print_container_size = models.BooleanField(default=False)
    seal_numbers = models.CharField(max_length=500, blank=True, null=True)
    commodity_description = models.TextField(blank=True, null=True)
    net_weight_unit = models.CharField(max_length=50, blank=True, null=True)
    gross_weight_unit = models.CharField(max_length=50, blank=True, null=True)

    target_commodity = models.BooleanField(default=False)
    target_container = models.BooleanField(default=False)
    target_packing = models.BooleanField(default=False)
    target_other = models.CharField(max_length=200, blank=True, null=True)

    prescribed_dose = models.CharField(max_length=100, blank=True, null=True)
    prescribed_exposure = models.CharField(max_length=100, blank=True, null=True)
    prescribed_temp = models.CharField(max_length=100, blank=True, null=True)

    applied_dose = models.CharField(max_length=100, blank=True, null=True)
    applied_exposure = models.CharField(max_length=100, blank=True, null=True)
    applied_temp = models.CharField(max_length=100, blank=True, null=True)

    fumigation_street = models.CharField(max_length=200, blank=True, null=True)
    fumigation_city = models.CharField(max_length=100, blank=True, null=True)
    fumigation_country = models.CharField(max_length=100, blank=True, null=True)
    fumigation_postcode = models.CharField(max_length=50, blank=True, null=True)

    operator_name = models.CharField(max_length=200, blank=True, null=True)
    certificate_sign_date = models.DateField(blank=True, null=True)
    additional_declaration = models.TextField(blank=True, null=True)
    
    treatment_provider_id = models.CharField(max_length=100, blank=True, null=True)
    accreditation_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def completion_image(self):
        log = self.usage_logs.exclude(photo_proof='').first()
        if log:
            return log.photo_proof
        return None

    def __str__(self):
        if self.assigned_to:
            worker = self.assigned_to.get_full_name() or self.assigned_to.username
        else:
            workers = self.assigned_workers.all()
            worker = workers[0].get_full_name() or workers[0].username if workers else 'Unassigned'
        return (
            f"Job #{self.pk}: {self.container_number} — "
            f"{worker} "
            f"[{self.get_status_display()}] on {self.execution_date}"
        )

    class Meta:
        ordering = ['-execution_date', '-created_at']
        verbose_name = "Job"
        verbose_name_plural = "Jobs"


class InventoryUsageLog(models.Model):
    """
    Records which inventory items were checked out, used, and returned
    for a specific job.  Can be created directly by admins for retroactive
    jobs without field-worker involvement.
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='usage_logs'
    )

    amount_taken = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        help_text="Units checked out from the warehouse (supports decimals, e.g. 0.4 L)."
    )
    amount_used = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        help_text="Units actually consumed on-site (supports decimals)."
    )
    amount_returned = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        help_text="Units brought back to the warehouse (supports decimals)."
    )

    photo_proof = models.ImageField(
        upload_to='return_proofs/',
        blank=True,
        null=True,
        help_text="Photo showing remaining / returned bottles."
    )

    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text=(
            "Admin-only notes for this log entry "
            "(e.g. reason for retroactive entry)."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name} → {self.job.container_number}"

    @property
    def is_balanced(self):
        """True when taken == used + returned."""
        return self.amount_taken == (self.amount_used + self.amount_returned)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inventory Usage Log"
        verbose_name_plural = "Inventory Usage Logs"


class JobImage(models.Model):
    """
    Stores multiple proof-of-work images for a single Job.
    Replaces the single photo_proof field on InventoryUsageLog
    for proof-of-work gallery functionality.
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='images',
        help_text="The job this image belongs to."
    )
    image = models.ImageField(
        upload_to='job_images/',
        help_text="Proof-of-work photo uploaded by the field worker."
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Job #{self.job.pk} ({self.job.container_number})"

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Job Image"
        verbose_name_plural = "Job Images"


# ---------------------------------------------------------------------------
# NOTE: Stock deduction is handled directly in views.py (job_detail_view)
# inside an atomic transaction for full control and proper error handling.
# The old signal that referenced the removed `total_stock` field has been
# removed to prevent silent transaction rollbacks.
# ---------------------------------------------------------------------------
