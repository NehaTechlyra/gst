from datetime import timedelta

from django.core.management.base import BaseCommand

from Lyraerp.scheduler import delete_expired_trial_databases_job


class Command(BaseCommand):
    help = "Delete unlicensed tenant databases seven days after trial expiry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List eligible companies without deleting databases",
        )
        parser.add_argument(
            "--keep-entries",
            action="store_true",
            help="Keep Company entries in main database (only mark as deleted). By default, Company entries are completely removed.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from django.utils import timezone
            from company.models import Company
            from company_settings.models import LicenseKey
            from django.db.models import Q
            from Lyraerp.utils.db_utils import database_exists, register_database

            now = timezone.now()
            grace_cutoff = now - timedelta(days=7)
            
            companies = Company.objects.using("default").filter(
                Q(db_created=True, db_name__isnull=False)
                | Q(db_name__isnull=True, trial_expires_at__lte=grace_cutoff)
            )
            
            eligible = []
            warning_pending = []
            
            for company in companies:
                try:
                    tenant_db_exists = database_exists(company.db_name)
                    license_obj = None

                    if tenant_db_exists:
                        register_database(company.db_name)
                        license_obj = LicenseKey.objects.using(company.db_name).filter(
                            company_id=company.pk,
                        ).first()

                    if license_obj and license_obj.expiry_date:
                        expiry_date = license_obj.expiry_date
                    elif company.trial_expires_at:
                        expiry_date = company.trial_expires_at.date() if hasattr(company.trial_expires_at, 'date') else company.trial_expires_at
                    elif not tenant_db_exists:
                        expiry_date = now.date() - timedelta(days=7)
                    else:
                        continue

                    # Check if in grace period
                    if hasattr(expiry_date, 'date'):
                        expiry_only = expiry_date.date()
                    else:
                        expiry_only = expiry_date
                    
                    days_past_expiry = (now.date() - expiry_only).days
                    
                    # Check for valid license
                    has_valid_license = bool(
                        license_obj
                        and license_obj.is_active
                        and not license_obj.is_license_expired
                        and (license_obj.expiry_date is None or license_obj.expiry_date >= now.date())
                    )
                    
                    if has_valid_license:
                        continue
                    
                    if 0 <= days_past_expiry < 7:
                        warning_pending.append({
                            'name': company.name,
                            'db_name': company.db_name,
                            'expiry_date': expiry_only,
                            'days_until_delete': 7 - days_past_expiry,
                            'warnings_sent': company.deletion_warning_email_count,
                        })
                    elif days_past_expiry >= 7:
                        eligible.append({
                            'name': company.name,
                            'db_name': company.db_name,
                            'expiry_date': expiry_only,
                        })
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Error processing {company.name}: {e}")
                    )
            
            # Show results
            if warning_pending:
                self.stdout.write(self.style.HTTP_INFO("DELETION WARNING PENDING (7-day grace period):"))
                for company in warning_pending:
                    self.stdout.write(
                        f"  {company['name']} | {company['db_name']} | "
                        f"Expired: {company['expiry_date']} | "
                        f"{company['days_until_delete']} days until deletion | "
                        f"Warnings sent: {company['warnings_sent']}/3"
                    )
            
            if eligible:
                self.stdout.write(self.style.WARNING("ELIGIBLE FOR DELETION:"))
                for company in eligible:
                    self.stdout.write(
                        f"  {company['name']} | {company['db_name']} | "
                        f"Expired: {company['expiry_date']}"
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDry run complete: {len(warning_pending)} in grace period, "
                    f"{len(eligible)} eligible for deletion"
                )
            )
            return

        result = delete_expired_trial_databases_job(
            dry_run=options["dry_run"],
            remove_company_entry=not options.get("keep_entries", False)
        )
        action = "eligible" if options["dry_run"] else "deleted"
        removal_mode = "archived" if options.get("keep_entries") else "completely removed"
        self.stdout.write(
            self.style.SUCCESS(
                f"Trial/license database cleanup complete: "
                f"{result['deleted']} {action} ({removal_mode}), "
                f"{result['skipped']} skipped, "
                f"{result['errors']} errors"
            )
        )
