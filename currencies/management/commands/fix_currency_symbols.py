from django.core.management.base import BaseCommand
from django.db import ProgrammingError


class Command(BaseCommand):
    help = (
        'Populate currency symbol and name fields for Currency rows where they are missing or '
        'equal to the ISO code. Use --all-companies to run across company databases.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--all-companies', action='store_true', help='Run fixer for all company DBs')

    def _fix_db(self, using='default'):
        try:
            from currencies.models import Currency
            from currencies.utils import get_currency_symbol, get_currency_name
        except Exception as e:
            self.stderr.write(f"Error importing modules: {e}")
            return 0

        updated = 0
        try:
            qs = Currency.objects.using(using).all()
        except ProgrammingError:
            self.stdout.write(f"Skipping DB '{using}': currencies table missing")
            return 0

        for cur in qs:
            code = (getattr(cur, 'code', '') or '').strip().upper()[:3]
            if not code:
                continue
            desired_sym = get_currency_symbol(code) or code
            desired_name = get_currency_name(code) or code
            changed = False
            if (not getattr(cur, 'symbol', None)) or (getattr(cur, 'symbol', '').strip() == code):
                cur.symbol = desired_sym
                changed = True
            if (not getattr(cur, 'name', None)) or (getattr(cur, 'name', '').strip().upper() == code):
                cur.name = desired_name
                changed = True
            if changed:
                cur.save(using=using, update_fields=['symbol', 'name'])
                updated += 1
        return updated

    def handle(self, *args, **options):
        all_companies = options.get('all_companies', False)

        if not all_companies:
            updated = self._fix_db(using='default')
            self.stdout.write(f"Updated {updated} currency rows in 'default'.")
            return

        # Run across company DBs
        try:
            from company.models import Company
            from Lyraerp.utils.db_utils import register_database
        except Exception as e:
            self.stderr.write(f"Error importing Company or db utils: {e}")
            return

        total = 0
        companies = Company.objects.using('default').all()
        if not companies:
            self.stdout.write('No companies found in master DB')
            return

        for comp in companies:
            dbname = comp.db_name or ''
            if not dbname:
                self.stdout.write(f"Company {comp.id} has no db_name, skipping")
                continue
            try:
                register_database(dbname)
                updated = self._fix_db(using=dbname)
                self.stdout.write(f"Company {comp.id} ({dbname}): updated {updated} rows")
                total += updated
            except Exception as e:
                self.stderr.write(f"Failed for company {comp.id} ({dbname}): {e}")

        self.stdout.write(f"Total updated across companies: {total}")
