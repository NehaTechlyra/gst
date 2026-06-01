from django.core.management.base import BaseCommand
from user.models import Module, PermissionType, Role, RolePermission, User
from django.contrib.auth.models import User as DjangoUser

class Command(BaseCommand):
    help = 'Diagnose user permissions'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to check')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        self.stdout.write(f"\nChecking permissions for user: {username}")
        
        # 1. Check if user exists in both auth and app
        try:
            django_user = DjangoUser.objects.get(username=username)
            self.stdout.write(f"✓ Found Django auth user: {django_user.username}")
            self.stdout.write(f"  Is superuser: {django_user.is_superuser}")
        except DjangoUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ No Django auth user found with username: {username}"))
            
        try:
            app_user = User.objects.get(usr_name=username)
            self.stdout.write(f"✓ Found app user: {app_user.usr_name}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ No app user found with username: {username}"))
            return

        # 2. Check role
        if not app_user.usr_roleid:
            self.stdout.write(self.style.ERROR("✗ User has no role assigned"))
            return
        
        role = app_user.usr_roleid
        self.stdout.write(f"✓ User has role: {role.role_name}")

        # 3. Check Sales module
        try:
            sales_module = Module.objects.get(name='Sales')
            self.stdout.write(f"✓ Sales module exists")
        except Module.DoesNotExist:
            self.stdout.write(self.style.ERROR("✗ Sales module not found"))
            sales_module = None

        if sales_module:
            # 4. Check permissions
            self.stdout.write("\nPermissions for Sales module:")
            perms = RolePermission.objects.filter(
                role=role,
                module=sales_module
            ).select_related('permission_type')
            
            if not perms.exists():
                self.stdout.write(self.style.ERROR("✗ No permissions found for Sales module"))
            else:
                for perm in perms:
                    status = "✓" if perm.allowed else "✗"
                    self.stdout.write(f"{status} {perm.permission_type.name}: {perm.allowed}")
                    
        # 5. List all modules this role has access to
        self.stdout.write("\nAll accessible modules:")
        accessible_modules = Module.objects.filter(
            rolepermission__role=role,
            rolepermission__allowed=True,
            rolepermission__permission_type__name='View'
        ).distinct()
        
        for module in accessible_modules:
            self.stdout.write(f"- {module.name}")