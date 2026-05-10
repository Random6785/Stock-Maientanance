from django.contrib import admin
from django.utils.html import format_html
from .models import InventoryItem, Job, InventoryUsageLog, WarehouseLocation, StockLevel, JobImage


# ---------------------------------------------------------------------------
# Inline: InventoryUsageLog entries shown inside a Job's detail page
# ---------------------------------------------------------------------------
class InventoryUsageLogInline(admin.StackedInline):
    """
    Allows admins to create / edit inventory usage logs directly on
    the Job change page — no need to navigate away.
    """
    model = InventoryUsageLog
    extra = 1                   # One blank row ready for entry by default
    min_num = 0
    can_delete = True
    show_change_link = True     # Link to the full standalone log form

    fields = (
        'item',
        ('amount_taken', 'amount_used', 'amount_returned'),
        'photo_proof',
        'admin_notes',
    )
    readonly_fields = ('balance_status',)

    def balance_status(self, obj):
        if obj.pk is None:
            return "—"
        if obj.is_balanced:
            return format_html('<span style="color:green;font-weight:bold;">✔ Balanced</span>')
        return format_html('<span style="color:red;font-weight:bold;">✘ Imbalanced</span>')
    balance_status.short_description = "Balance"


class JobImageInline(admin.TabularInline):
    """Shows proof-of-work images inline on the Job admin page."""
    model = JobImage
    extra = 0
    readonly_fields = ('image_preview', 'uploaded_at')
    fields = ('image', 'image_preview', 'uploaded_at')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px; border-radius:4px;" />', obj.image.url)
        return "—"
    image_preview.short_description = "Preview"


# ---------------------------------------------------------------------------
# Job Admin
# ---------------------------------------------------------------------------
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """
    Full-featured admin for retroactive job management.
    Admins can create, modify and backdate jobs without field-worker actions.
    """

    # --- List view ---
    list_display = (
        'container_number',
        'assigned_to',
        'status',
        'scheduled_date',
        'execution_date',
        'log_count',
        'updated_at',
    )
    list_filter = ('status', 'assigned_to', 'execution_date', 'scheduled_date')
    search_fields = ('container_number', 'assigned_to__username', 'assigned_to__first_name')
    date_hierarchy = 'execution_date'       # Drill-down by actual execution date

    # Make these columns directly editable in the list view
    list_editable = ('status', 'execution_date')

    # --- Detail / Change view ---
    fieldsets = (
        ('Job Details', {
            'fields': (
                'container_number',
                'assigned_to',
                'status',
            )
        }),
        ('Dates', {
            'description': (
                '<strong>execution_date</strong> is the actual date the job was performed. '
                'Admins may backdate this field freely for retroactive entry.'
            ),
            'fields': (
                'scheduled_date',
                'execution_date',
            )
        }),
        ('Notes', {
            'classes': ('collapse',),
            'fields': ('notes',),
        }),
        ('Audit', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    # Inline usage logs and images on the same page
    inlines = [InventoryUsageLogInline, JobImageInline]

    # Handy shortcuts
    save_on_top = True          # Save buttons appear at the top too
    save_as = True              # "Save as new" — useful for cloning past jobs

    # --- Custom columns ---
    @admin.display(description='Usage Logs')
    def log_count(self, obj):
        count = obj.usage_logs.count()
        return format_html(
            '<span style="font-weight:bold;">{}</span>', count
        )

    # --- Quick-filter actions ---
    actions = ['mark_completed', 'mark_pending', 'mark_in_progress']

    @admin.action(description='Mark selected jobs as Completed')
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} job(s) marked as Completed.")

    @admin.action(description='Mark selected jobs as Pending')
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f"{updated} job(s) marked as Pending.")

    @admin.action(description='Mark selected jobs as In Progress')
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f"{updated} job(s) marked as In Progress.")


# ---------------------------------------------------------------------------
# StockLevel Inline — shown inside InventoryItem and WarehouseLocation pages
# ---------------------------------------------------------------------------
class StockLevelInline(admin.TabularInline):
    model = StockLevel
    extra = 1
    fields = ('location', 'quantity')
    autocomplete_fields = []

    def get_autocomplete_fields(self, request):
        return []


# ---------------------------------------------------------------------------
# Inventory Item Admin
# ---------------------------------------------------------------------------
@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_of_measurement', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [StockLevelInline]


# ---------------------------------------------------------------------------
# Warehouse Location Admin
# ---------------------------------------------------------------------------
class StockLevelByItemInline(admin.TabularInline):
    model = StockLevel
    extra = 1
    fields = ('item', 'quantity')
    verbose_name = "Item Stock"
    verbose_name_plural = "Item Stock Levels"


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'address', 'total_units')
    search_fields = ('name', 'address')
    inlines       = [StockLevelByItemInline]

    @admin.display(description='Total Units Stored')
    def total_units(self, obj):
        from django.db.models import Sum
        total = obj.stock_levels.aggregate(t=Sum('quantity'))['t'] or 0
        return total


# ---------------------------------------------------------------------------
# StockLevel Admin (standalone — for bulk review / editing)
# ---------------------------------------------------------------------------
@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display  = ('item', 'location', 'quantity')
    list_editable = ('quantity',)
    list_filter   = ('location',)
    search_fields = ('item__name', 'location__name')
    autocomplete_fields = ['item', 'location']


# ---------------------------------------------------------------------------
# Inventory Usage Log Admin (standalone — for direct retroactive creation)
# ---------------------------------------------------------------------------
@admin.register(InventoryUsageLog)
class InventoryUsageLogAdmin(admin.ModelAdmin):
    """
    Standalone admin for InventoryUsageLog.
    Admins can create logs here directly and link them to any existing job,
    enabling fully retroactive data entry without going through the job form.
    """
    list_display = (
        'job',
        'item',
        'amount_taken',
        'amount_used',
        'amount_returned',
        'balance_indicator',
        'photo_proof',
        'created_at',
    )
    list_filter = ('job__status', 'item')
    search_fields = ('job__container_number', 'item__name')
    autocomplete_fields = ['job', 'item']    # Searchable dropdowns for large datasets
    readonly_fields = ('created_at', 'updated_at', 'balance_indicator')

    fieldsets = (
        ('Link to Job', {
            'fields': ('job',)
        }),
        ('Item & Quantities', {
            'fields': (
                'item',
                ('amount_taken', 'amount_used', 'amount_returned'),
                'balance_indicator',
            )
        }),
        ('Evidence', {
            'fields': ('photo_proof',)
        }),
        ('Admin Notes', {
            'classes': ('collapse',),
            'fields': ('admin_notes',),
        }),
        ('Audit', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Balanced?', boolean=True)
    def balance_indicator(self, obj):
        if obj.pk is None:
            return None
        return obj.is_balanced
