from django.contrib import admin
from user.models import RightsDtl, User, Module, PermissionType, Role, RolePermission

# Register all models
admin.site.register(RightsDtl)
admin.site.register(User)
admin.site.register(Module)
admin.site.register(PermissionType)
admin.site.register(Role)
admin.site.register(RolePermission)