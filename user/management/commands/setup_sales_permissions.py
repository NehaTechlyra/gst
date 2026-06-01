from django.core.management.base import BaseCommand
from user.models import Module, PermissionType, Role, RolePermission

class Command(BaseCommand):
    help = 'Sets up Sales module and permissions'

    def handle(self, *args, **kwargs):
        # Create Sales module if it doesn't exist
        sales_module, created = Module.objects.get_or_create(name='Sales')
        if created:
            self.stdout.write(self.style.SUCCESS('Created Sales module'))

        # Ensure we have basic permission types
        permission_types = ['View', 'Create', 'Edit', 'Delete', 'Full Access']
        for perm_type in permission_types:
            PermissionType.objects.get_or_create(name=perm_type)

        # Get all roles
        roles = Role.objects.all()

        # For each role, ensure Sales permissions exist
        for role in roles:
            for perm_type in PermissionType.objects.all():
                RolePermission.objects.get_or_create(
                    role=role,
                    module=sales_module,
                    permission_type=perm_type,
                    defaults={'allowed': True if role.role_name == 'Administrator' else False}
                )
            
        self.stdout.write(self.style.SUCCESS('Successfully set up Sales permissions'))