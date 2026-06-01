from django.contrib import admin
from stock.models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = [
        'item',
        'warehouse',
        'quantity',
        'batch_number',
        'opening_stock',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'warehouse', 'created_at']
    search_fields = ['item__name', 'warehouse__warehouse_name', 'batch_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('item', 'warehouse', 'quantity', 'status')
        }),
        ('Batch & Serial', {
            'fields': ('batch_number', 'serial_number', 'expiration_date'),
            'classes': ('collapse',)
        }),
        ('Opening Stock', {
            'fields': ('opening_stock',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

