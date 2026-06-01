from django.contrib import admin

# Register your models here.
# Register your models here.
from sales.models import SalesQuotation, EWayBill

# Register your models here.
admin.site.register(SalesQuotation)


@admin.register(EWayBill)
class EWayBillAdmin(admin.ModelAdmin):
    list_display   = [
        'ewb_number', 'invoice', 'status', 'total_value',
        'mode_of_transport', 'vehicle_number', 'generated_at', 'created_at',
    ]
    list_filter    = ['status', 'mode_of_transport', 'vehicle_type']
    search_fields  = ['ewb_number', 'invoice__inv_number', 'gstin_from', 'gstin_to']
    readonly_fields = ['ewb_number', 'generated_at', 'created_at', 'updated_at']
    fieldsets = (
        ('Invoice Link', {
            'fields': ('invoice', 'status', 'ewb_number', 'total_value'),
        }),
        ('Parties', {
            'fields': (
                ('gstin_from', 'place_from', 'pincode_from', 'state_from'),
                ('gstin_to',   'place_to',   'pincode_to',   'state_to'),
            ),
        }),
        ('Transport', {
            'fields': (
                'mode_of_transport', 'vehicle_number', 'vehicle_type',
                'transporter_id', 'transporter_name',
                'transport_doc_no', 'transport_doc_date',
                'approximate_distance',
            ),
        }),
        ('Goods', {
            'fields': ('hsn_code',),
        }),
        ('Timestamps', {
            'fields': ('generated_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )