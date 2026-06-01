"""
Management command to reset is_license_expired flag for active licenses that have not yet expired.

This command fixes cases where active licenses with future expiry dates still have 
is_license_expired=1 (True) from previously expired licenses.

Usage:
    python manage.py reset_active_license_flags
    
This will:
1. Find all active licenses with future expiry dates where is_license_expired=1
2. Reset is_license_expired to 0 (False)
3. Log all actions taken
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from company_settings.models import LicenseKey
from company.models import Company
from Lyraerp.utils.db_utils import register_database
from django.db import ProgrammingError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset is_license_expired flag for active licenses that have not yet expired'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting license flag reset...'))
        
        fixed_count = 0
        skipped = 0
        errors = 0
        today = timezone.now().date()

        try:
            # Get all companies from master DB
            companies = Company.objects.using('default').filter(db_created=True)
            
            for company in companies:
                try:
                    company_db = company.db_name
                    if not company_db:
                        skipped += 1
                        continue
                    
                    # Register the database connection
                    register_database(company_db)
                    
                    try:
                        # Find active licenses with future expiry dates that are incorrectly marked as expired
                        licenses = LicenseKey.objects.using(company_db).filter(
                            is_active=True,
                            is_license_expired=True,
                            expiry_date__gt=today  # expiry_date is in the future
                        )
                        
                        for lic in licenses:
                            try:
                                lic.is_license_expired = False
                                lic.save(using=company_db, update_fields=['is_license_expired'])
                                fixed_count += 1
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✓ Fixed [{company.name}] {lic.license_key[:10]}... '
                                        f'(expires: {lic.expiry_date})'
                                    )
                                )
                                logger.info(
                                    f"[LICENSE FIX] Reset is_license_expired for {lic.license_key} "
                                    f"in {company.name} (expires: {lic.expiry_date})"
                                )
                            except Exception as e:
                                errors += 1
                                logger.error(
                                    f"[LICENSE FIX] Error fixing license {getattr(lic, 'id', '?')} "
                                    f"in {company.name}: {e}", 
                                    exc_info=True
                                )
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'✗ Error fixing license in {company.name}: {e}'
                                    )
                                )
                                
                    except ProgrammingError as e:
                        # Table doesn't exist yet in this company's DB
                        logger.debug(
                            f"[LICENSE FIX] LicenseKey table doesn't exist in {company.name}: {e}"
                        )
                        skipped += 1
                    
                except Exception as e:
                    errors += 1
                    logger.error(
                        f"[LICENSE FIX] Error processing company {company.name}: {e}", 
                        exc_info=True
                    )
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {company.name}: {e}')
                    )
            
        except Exception as e:
            logger.error(f"[LICENSE FIX] Command error: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Command failed: {e}'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ License flag reset completed:\n'
                f'  - {fixed_count} license(s) fixed\n'
                f'  - {skipped} company database(s) skipped\n'
                f'  - {errors} error(s) encountered'
            )
        )
        
        if fixed_count > 0:
            logger.info(
                f"[LICENSE FIX] Command completed: {fixed_count} licenses fixed, "
                f"{skipped} skipped, {errors} errors"
            )
