from django.core.management.base import BaseCommand
from django.contrib.auth.models import User as DjangoUser
from django.test import RequestFactory
from user.context_processors import permissions_for_request


class Command(BaseCommand):
    help = 'Debug session and permissions for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to debug')

    def handle(self, *args, **options):
        username = options['username']
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"🐛 DEBUG SESSION FOR: {username}")
        self.stdout.write(f"{'='*60}\n")
        
        # Get user
        try:
            user = DjangoUser.objects.using('default').get(username=username)
            self.stdout.write(self.style.SUCCESS(f"✅ Found user: {username}"))
        except DjangoUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User not found: {username}"))
            return
        
        # Create mock request
        factory = RequestFactory()
        request = factory.get('/')
        request.user = user
        
        # Simulate session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add session data (simulate login)
        from user.models import User as CustomUser
        try:
            custom_user = CustomUser.objects.using('default').get(usr_name=username)
            role = custom_user.usr_roleid
            company = role.company if role else None
            
            if company:
                request.session['login_username'] = username
                request.session['usr_roleid'] = role.id
                request.session['company_id'] = company.id
                request.session['company_db'] = company.db_name
                request.session['is_superadmin'] = False
                request.session.save()
                
                self.stdout.write(f"\n📋 SESSION DATA:")
                self.stdout.write(f"  - login_username: {request.session.get('login_username')}")
                self.stdout.write(f"  - usr_roleid: {request.session.get('usr_roleid')}")
                self.stdout.write(f"  - company_id: {request.session.get('company_id')}")
                self.stdout.write(f"  - company_db: {request.session.get('company_db')}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error setting up session: {e}"))
            return
        
        # Get context from processor
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("🔍 CONTEXT PROCESSOR OUTPUT:")
        self.stdout.write(f"{'─'*60}")
        
        try:
            context = permissions_for_request(request)
            
            self.stdout.write(f"\n📊 visible_modules ({len(context.get('visible_modules', []))}):")
            for mod in sorted(context.get('visible_modules', [])):
                self.stdout.write(f"  - {mod}")
            
            self.stdout.write(f"\n🔐 user_permissions:")
            for module, perms in sorted(context.get('user_permissions', {}).items()):
                perm_list = [k for k, v in perms.items() if v]
                if perm_list:
                    self.stdout.write(f"  {module}:")
                    for p in perm_list:
                        self.stdout.write(f"    ✓ {p}")
            
            self.stdout.write(f"\n🔧 Individual Permission Flags:")
            individual_flags = [
                'can_view_quotations', 'can_view_orders', 'can_view_invoices',
                'can_view_payments_received', 'can_view_items', 'can_view_customers',
                'can_view_users', 'can_view_user_roles', 'can_view_warehouse',
                'can_view_vendors', 'can_view_taxes', 'can_view_stock',
                'can_view_payterms', 'can_view_brands', 'can_view_units'
            ]
            
            for flag in individual_flags:
                value = context.get(flag, False)
                status = "✅" if value else "❌"
                self.stdout.write(f"  {status} {flag}: {value}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error getting context: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("✅ DEBUG COMPLETE")
        self.stdout.write(f"{'='*60}\n")