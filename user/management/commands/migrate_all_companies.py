from django.core.management.base import BaseCommand
from user.models import Company
from Lyraerp.utils.db_utils import migrate_company_database
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate all company databases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Migrate specific company by ID',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        
        if company_id:
            companies = Company.objects.filter(id=company_id)
        else:
            # Only attempt migrations for companies whose databases were created
            # (the `status` field does not exist on Company)
            companies = Company.objects.filter(db_created=True)
        
        total = companies.count()
        self.stdout.write(f'Found {total} companies to migrate')
        
        success_count = 0
        failed_count = 0
        
        for company in companies:
            if company.db_name:
                self.stdout.write(f'\nMigrating {company.db_name} ({company.name})...')
                try:
                    migrate_company_database(company.db_name)
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Successfully migrated {company.db_name}')
                    )
                    success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Failed to migrate {company.db_name}: {e}')
                    )
                    logger.error(f"Migration failed for {company.db_name}", exc_info=True)
                    failed_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Skipping {company.name} - no database name')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✅ Successful: {success_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {failed_count}'))
        self.stdout.write('='*50)