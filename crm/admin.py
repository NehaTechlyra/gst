# from django.contrib import admin
# from .models import (
#     LostReason, Lead, Opportunity, Update, FollowUp
# )


# @admin.register(LostReason)
# class LostReasonAdmin(admin.ModelAdmin):
#     list_display = ['reason', 'created_at']
#     search_fields = ['reason']


# @admin.register(Lead)
# class LeadAdmin(admin.ModelAdmin):
#     list_display = ['customer_name', 'phone', 'product_interested', 'priority', 'status', 'assigned_to', 'created_at']
#     list_filter = ['priority', 'status', 'source', 'assigned_to', 'created_at']
#     search_fields = ['customer_name', 'phone', 'email', 'product_interested']
#     date_hierarchy = 'created_at'


# @admin.register(Opportunity)
# class OpportunityAdmin(admin.ModelAdmin):
#     list_display = ['lead', 'estimated_deal_value', 'status', 'priority', 'expected_closing_date', 'assigned_to']
#     list_filter = ['status', 'priority', 'assigned_to', 'created_at']
#     search_fields = ['lead__customer_name', 'products_quantities']



# @admin.register(Update)
# class UpdateAdmin(admin.ModelAdmin):
#     list_display = ['update_type', 'lead', 'opportunity', 'quotation', 'created_by', 'created_at']
#     list_filter = ['update_type', 'created_at']
#     search_fields = ['description']


# @admin.register(FollowUp)
# class FollowUpAdmin(admin.ModelAdmin):
#     list_display = ['description', 'followup_date', 'status', 'assigned_to', 'reminder_sent', 'created_at']
#     list_filter = ['status', 'reminder_sent', 'assigned_to', 'followup_date']
#     search_fields = ['description']
