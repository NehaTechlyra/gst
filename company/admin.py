from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'company_code',
        'email',
        'phone',
        'status',
        'setup_complete',
        'stock_management_on_delivery',
        'db_created',
        'trial_active',
        'is_trial_expired',
        'created_at',
    )
    list_filter = (
        'status',
        'setup_complete',
        'db_created',
        'trial_active',
        'is_trial_expired',
        'stock_management_on_delivery',
        'country',
        'tax_type',
    )
    search_fields = (
        'name',
        'legal_name',
        'company_code',
        'company_id',
        'email',
        'phone',
        'contact_person',
        'contact_email',
        'db_name',
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

