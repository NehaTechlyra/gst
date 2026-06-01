from django.core.management.base import BaseCommand
from Lyraerp.utils.license_utils import (
    generate_full_license,
    generate_custom_license,
    generate_trial_license,
    parse_license_key
)


class Command(BaseCommand):
    help = 'Generate license keys for testing'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, choices=['full', 'custom', 'trial'], default='full')
        parser.add_argument('--company', type=str, default='Test Company')
        parser.add_argument('--modules', type=str, help='Comma-separated list (e.g., "Sales,CRM,HR")')
        parser.add_argument('--users', type=int, default=50)
        parser.add_argument('--years', type=int, default=1)

    def handle(self, *args, **options):
        company_name = options['company']
        license_type = options['type']
        max_users = options['users']
        years = options['years']
        
        if license_type == 'full':
            license_key = generate_full_license(company_name, max_users, years)
            self.stdout.write(f"\n✅ FULL LICENSE GENERATED:")
            
        elif license_type == 'custom':
            if not options['modules']:
                self.stdout.write(self.style.ERROR("--modules required for custom license"))
                return
            modules = [m.strip() for m in options['modules'].split(',')]
            license_key = generate_custom_license(company_name, modules, max_users, years)
            self.stdout.write(f"\n✅ CUSTOM LICENSE GENERATED:")
            self.stdout.write(f"   Modules: {modules}")
            
        elif license_type == 'trial':
            if not options['modules']:
                modules = ['Sales', 'CRM']
            else:
                modules = [m.strip() for m in options['modules'].split(',')]
            license_key = generate_trial_license(company_name, modules)
            self.stdout.write(f"\n✅ TRIAL LICENSE GENERATED:")
            self.stdout.write(f"   Modules: {modules}")
        
        self.stdout.write(f"\nCompany: {company_name}")
        self.stdout.write(f"License Key:\n{license_key}")
        
        # Parse and display
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("LICENSE DETAILS:")
        self.stdout.write(f"{'─'*60}")
        
        details = parse_license_key(license_key)
        for key, value in details.items():
            self.stdout.write(f"  {key}: {value}")
        
        self.stdout.write(f"\n{'─'*60}")
        self.stdout.write("TO USE:")
        self.stdout.write(f"{'─'*60}")
        self.stdout.write(f"Update company.license_key with the above key")
        self.stdout.write("")