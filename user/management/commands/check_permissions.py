from django.core.management.base import BaseCommand
from user.models import Module, RolePermission, Role, User
from django.db import connections
from Lyraerp.utils.db_utils import register_database
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check permissions setup for a company database'

    def add_arguments(self, parser):
        parser.add_argument('db_name', type=str, help='Company database name')
        parser.add_argument('--username', type=str, help='Username to check', default=None)
        parser.add_argument('--fix', action='store_true', help='Attempt to fix permission issues')

    def handle(self, *args, **options):
        db_name = options['db_name']
        username = options.get('username')
        fix_mode = options.get('fix', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"📊 CHECKING PERMISSIONS FOR: {db_name}")
        self.stdout.write(f"{'='*60}\n")

        # ✅ REGISTER DATABASE FIRST
        self.stdout.write("🔧 Registering database connection...")
        try:
            register_database(db_name)
            self.stdout.write(self.style.SUCCESS(f"✅ Database registered: {db_name}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to register database: {e}"))
            return

        # Check database exists and connection works
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS(f"✅ Database connection successful"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection failed: {e}"))
            self.stdout.write(f"\nDatabase might not exist. Available databases:")
            with connections['default'].cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                for row in cursor.fetchall():
                    self.stdout.write(f"  - {row[0]}")
            return

        # Check modules
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("📦 MODULES:")
        self.stdout.write(f"{'─'*60}")
        
        try:
            modules = Module.objects.using(db_name).all()
            self.stdout.write(f"Total: {modules.count()}")
            
            if modules.count() == 0:
                self.stdout.write(self.style.ERROR("❌ NO MODULES FOUND!"))
                
                if fix_mode:
                    self.stdout.write(self.style.WARNING("🔧 Attempting to populate modules..."))
                    try:
                        from Lyraerp.utils.db_utils import populate_modules_from_license
                        populate_modules_from_license(db_name, None)  # None = all modules
                        self.stdout.write(self.style.SUCCESS("✅ Modules populated"))
                        modules = Module.objects.using(db_name).all()
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Failed to populate modules: {e}"))
                        import traceback
                        self.stdout.write(traceback.format_exc())
            
            for m in modules:
                self.stdout.write(f"   {m.id:3d}: {m.name}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error querying modules: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

        # Check permission types
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("🔐 PERMISSION TYPES:")
        self.stdout.write(f"{'─'*60}")
        
        try:
            from user.models import PermissionType
            perm_types = PermissionType.objects.using(db_name).all()
            self.stdout.write(f"Total: {perm_types.count()}")
            
            if perm_types.count() == 0:
                self.stdout.write(self.style.ERROR("❌ NO PERMISSION TYPES FOUND!"))
                
                if fix_mode:
                    self.stdout.write(self.style.WARNING("🔧 Attempting to populate permission types..."))
                    try:
                        from Lyraerp.utils.db_utils import populate_permission_types
                        populate_permission_types(db_name)
                        self.stdout.write(self.style.SUCCESS("✅ Permission types populated"))
                        perm_types = PermissionType.objects.using(db_name).all()
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Failed to populate permission types: {e}"))
                        import traceback
                        self.stdout.write(traceback.format_exc())
            
            for pt in perm_types:
                self.stdout.write(f"   {pt.id:3d}: {pt.name}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error querying permission types: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

        # Check roles
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("👥 ROLES:")
        self.stdout.write(f"{'─'*60}")
        
        try:
            roles = Role.objects.using(db_name).all()
            self.stdout.write(f"Total: {roles.count()}")
            
            for r in roles:
                perm_count = RolePermission.objects.using(db_name).filter(role=r, allowed=1).count()
                total_count = RolePermission.objects.using(db_name).filter(role=r).count()
                
                self.stdout.write(f"   {r.id:3d}: {r.role_name} (Permissions: {perm_count} active / {total_count} total)")
                
                if perm_count == 0 and total_count > 0:
                    self.stdout.write(self.style.WARNING(f"       ⚠️ All permissions are disabled (allowed=0)"))
                    
                    if fix_mode:
                        self.stdout.write(self.style.WARNING("       🔧 Enabling all permissions..."))
                        try:
                            RolePermission.objects.using(db_name).filter(role=r).update(allowed=1)
                            self.stdout.write(self.style.SUCCESS(f"       ✅ Enabled {total_count} permissions"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"       ❌ Failed to enable permissions: {e}"))
                
                if perm_count == 0 and total_count == 0:
                    self.stdout.write(self.style.ERROR(f"       ❌ No permissions exist for this role"))
                    
                    if fix_mode and r.role_name == "Admin":
                        self.stdout.write(self.style.WARNING("       🔧 Creating admin permissions..."))
                        try:
                            from Lyraerp.utils.db_utils import create_admin_role_permissions
                            create_admin_role_permissions(db_name, r.id)
                            perm_count = RolePermission.objects.using(db_name).filter(role=r, allowed=1).count()
                            self.stdout.write(self.style.SUCCESS(f"       ✅ Created {perm_count} permissions"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"       ❌ Failed to create permissions: {e}"))
                            import traceback
                            self.stdout.write(traceback.format_exc())
                            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error querying roles: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

        # Check specific user permissions
        if username:
            self.stdout.write(f"\n{'─'*60}")
            self.stdout.write(f"👤 USER PERMISSIONS: {username}")
            self.stdout.write(f"{'─'*60}")
            
            try:
                user = User.objects.using(db_name).filter(usr_name=username).first()
                
                if not user:
                    self.stdout.write(self.style.ERROR(f"❌ User '{username}' not found in {db_name}"))
                elif not user.usr_roleid:
                    self.stdout.write(self.style.ERROR(f"❌ User '{username}' has no role assigned"))
                else:
                    role = user.usr_roleid
                    self.stdout.write(f"Role: {role.role_name} (ID: {role.id})")
                    
                    perms = RolePermission.objects.using(db_name).filter(
                        role=role,
                        allowed=1
                    ).select_related('module', 'permission_type').order_by('module__name', 'permission_type__id')
                    
                    if perms.count() == 0:
                        self.stdout.write(self.style.ERROR("❌ NO ACTIVE PERMISSIONS FOUND"))
                        
                        # Check if permissions exist but disabled
                        all_perms = RolePermission.objects.using(db_name).filter(role=role).count()
                        if all_perms > 0:
                            self.stdout.write(self.style.WARNING(f"⚠️ Found {all_perms} permissions but all are disabled"))
                        else:
                            self.stdout.write(self.style.ERROR("❌ No permissions exist for this role at all"))
                    else:
                        self.stdout.write(f"\nActive Permissions ({perms.count()}):\n")
                        
                        current_module = None
                        for p in perms:
                            if current_module != p.module.name:
                                current_module = p.module.name
                                self.stdout.write(f"\n   📦 {current_module}:")
                            self.stdout.write(f"      ✓ {p.permission_type.name}")
                    
                    # Check what visible_modules would be
                    visible = [p.module.name for p in perms if p.permission_type.name in ['View', 'Full Access']]
                    visible_unique = list(set(visible))
                    
                    self.stdout.write(f"\n📋 Visible Modules ({len(visible_unique)}):")
                    for vm in sorted(visible_unique):
                        self.stdout.write(f"   - {vm}")
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error checking user permissions: {e}"))
                import traceback
                self.stdout.write(traceback.format_exc())

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("✅ CHECK COMPLETE")
        self.stdout.write(f"{'='*60}\n")
        
        if not fix_mode:
            has_issues = False
            try:
                if Module.objects.using(db_name).count() == 0:
                    has_issues = True
            except:
                pass
            
            try:
                from user.models import PermissionType
                if PermissionType.objects.using(db_name).count() == 0:
                    has_issues = True
            except:
                pass
            
            if has_issues:
                self.stdout.write(self.style.WARNING("\n💡 TIP: Run with --fix to attempt automatic repairs"))
                self.stdout.write("   Example: python manage.py check_permissions lyra_techlyrainfosystem_1 --fix")