# from django.contrib import admin
# from django.utils.html import format_html
# from .models import FiscalYear, PeriodLock, PeriodLockExemption


# @admin.register(FiscalYear)
# class FiscalYearAdmin(admin.ModelAdmin):
#     list_display = (
#         'name', 
#         'start_date', 
#         'end_date', 
#         'status',
#         'lock_status_display',
#         'locked_by',
#         'lock_date'
#     )
    
#     list_filter = (
#         'status',
#         'is_locked',
#         'start_date',
#         'created_at'
#     )
    
#     search_fields = ('name',)
    
#     readonly_fields = (
#         'lock_date',
#         'locked_by',
#         'created_at',
#         'updated_at',
#         'created_by'
#     )
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('name', 'status', 'start_date', 'end_date')
#         }),
#         ('Locking Status', {
#             'fields': ('is_locked', 'lock_date', 'locked_by'),
#             'classes': ('collapse',)
#         }),
#         ('Audit Trail', {
#             'fields': ('created_at', 'updated_at', 'created_by'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     actions = ['lock_fiscal_year', 'unlock_fiscal_year']
    
#     def lock_status_display(self, obj):
#         """Display lock status with color coding"""
#         if obj.is_locked:
#             return format_html(
#                 '<span style="color: red; font-weight: bold;">🔒 LOCKED</span>'
#             )
#         return format_html(
#             '<span style="color: green; font-weight: bold;">🔓 OPEN</span>'
#         )
#     lock_status_display.short_description = 'Lock Status'
    
#     def lock_fiscal_year(self, request, queryset):
#         """Admin action to lock selected fiscal years"""
#         for fiscal_year in queryset:
#             fiscal_year.lock(user=request.user)
#         self.message_user(request, f"{queryset.count()} fiscal year(s) locked.")
#     lock_fiscal_year.short_description = "🔒 Lock selected fiscal years"
    
#     def unlock_fiscal_year(self, request, queryset):
#         """Admin action to unlock selected fiscal years"""
#         for fiscal_year in queryset:
#             fiscal_year.unlock()
#         self.message_user(request, f"{queryset.count()} fiscal year(s) unlocked.")
#     unlock_fiscal_year.short_description = "🔓 Unlock selected fiscal years"


# @admin.register(PeriodLock)
# class PeriodLockAdmin(admin.ModelAdmin):
#     list_display = (
#         'fiscal_year',
#         'action',
#         'performed_by',
#         'performed_at'
#     )
    
#     list_filter = (
#         'action',
#         'performed_at',
#         'fiscal_year'
#     )
    
#     search_fields = (
#         'fiscal_year__name',
#         'performed_by__username'
#     )
    
#     readonly_fields = (
#         'fiscal_year',
#         'action',
#         'performed_by',
#         'performed_at',
#         'reason'
#     )
    
#     can_delete = False  # Prevent deletion of audit records


# @admin.register(PeriodLockExemption)
# class PeriodLockExemptionAdmin(admin.ModelAdmin):
#     list_display = (
#         'user',
#         'fiscal_year',
#         'granted_at',
#         'granted_by'
#     )
    
#     list_filter = (
#         'fiscal_year',
#         'granted_at'
#     )
    
#     search_fields = (
#         'user__username',
#         'fiscal_year__name'
#     )
    
#     readonly_fields = (
#         'granted_at',
#         'granted_by'
#     )
    
#     fields = (
#         'fiscal_year',
#         'user',
#         'reason',
#         'granted_at',
#         'granted_by'
#     )
    
#     def save_model(self, request, obj, form, change):
#         """Set granted_by to current user when creating exemptions"""
#         if not change:
#             obj.granted_by = request.user
#         super().save_model(request, obj, form, change)
