from django.core.management.base import BaseCommand
from user.models import Module, PermissionType, Role, RolePermission, User
from django.contrib.auth.models import User as DjangoUser

class Command(BaseCommand):
    help = 'Grants Sales permissions to a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to grant permissions to')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        
        try:
            django_user = DjangoUser.objects.get(username=username)
            app_user = User.objects.get(usr_name=username)
        except (DjangoUser.DoesNotExist, User.DoesNotExist):
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
            return

        # Get or create Sales module
        sales_module, _ = Module.objects.get_or_create(name='Sales')
        
        # Ensure role exists
        role = app_user.usr_roleid
        if not role:
            self.stdout.write(self.style.ERROR(f'User {username} has no role assigned'))
            return

        # Grant all Sales permissions
        for perm_type in PermissionType.objects.all():
            role_perm, created = RolePermission.objects.get_or_create(
                role=role,
                module=sales_module,
                permission_type=perm_type,
                defaults={'allowed': True}
            )
            if not created:
                role_perm.allowed = True
                role_perm.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully granted Sales permissions to {username}'))