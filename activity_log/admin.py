# from django.contrib import admin
# from .models import ActivityLog
# import json

# @admin.register(ActivityLog)
# class ActivityLogAdmin(admin.ModelAdmin):
#     list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr', 'ip_address']
#     list_filter = ['action', 'model_name', 'timestamp', 'user']
#     search_fields = ['object_repr', 'description', 'user__username']
#     readonly_fields = [
#         'user', 'action', 'content_type', 'object_id', 'object_repr',
#         'model_name', 'description', 'changes', 'old_values', 'new_values',
#         'ip_address', 'user_agent', 'timestamp', 'formatted_changes_display'
#     ]
#     date_hierarchy = 'timestamp'
    
#     def formatted_changes_display(self, obj):
#         """Display formatted changes in admin."""
#         if obj.changes:
#             return json.dumps(obj.formatted_changes, indent=2)
#         return '-'
#     formatted_changes_display.short_description = 'Changes (Formatted)'
    
#     def has_add_permission(self, request):
#         return False
    
#     def has_delete_permission(self, request, obj=None):
#         return request.user.is_superuser
