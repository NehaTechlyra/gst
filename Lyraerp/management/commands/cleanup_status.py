"""
Management command for database cleanup utilities.

Usage:
    python manage.py cleanup_status              # Show current cleanup status
    python manage.py cleanup_status --export json  # Export as JSON
    python manage.py cleanup_status --export csv   # Export as CSV
    python manage.py cleanup_status --export txt   # Export as text report
"""

from django.core.management.base import BaseCommand, CommandError
from Lyraerp.utils.cleanup_utils import (
    get_cleanup_summary,
    export_cleanup_report,
    manually_delete_company,
    get_companies_in_grace_period,
    get_companies_pending_deletion,
)


class Command(BaseCommand):
    help = "View and manage database cleanup status"

    def add_arguments(self, parser):
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show cleanup summary',
        )
        parser.add_argument(
            '--export',
            type=str,
            choices=['json', 'csv', 'txt'],
            help='Export report in specified format',
        )
        parser.add_argument(
            '--delete',
            type=int,
            metavar='COMPANY_ID',
            help='Manually delete a company by ID',
        )
        parser.add_argument(
            '--keep-entry',
            action='store_true',
            help='Archive company (keep entry) instead of complete removal',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion even if company has active license',
        )

    def handle(self, *args, **options):
        if options.get('delete'):
            self._handle_delete(options)
        elif options.get('export'):
            self._handle_export(options)
        elif options.get('summary'):
            self._show_summary()
        else:
            self._show_default()

    def _show_default(self):
        """Show default cleanup status overview."""
        summary = get_cleanup_summary()
        
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("DATABASE CLEANUP STATUS"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))
        
        self.stdout.write(
            f"Total Expired Companies: {self.style.HTTP_INFO(str(summary['total_expired']))}"
        )
        self.stdout.write(
            f"In Grace Period (< 7 days): {self.style.WARNING(str(summary['in_grace_period']))}"
        )
        self.stdout.write(
            f"Eligible for Deletion (>= 7 days): {self.style.ERROR(str(summary['eligible_for_deletion']))}\n"
        )
        
        if summary['grace_period_companies']:
            self.stdout.write(self.style.WARNING("COMPANIES IN GRACE PERIOD:"))
            self.stdout.write("-" * 80)
            for item in summary['grace_period_companies']:
                self.stdout.write(
                    f"  {item['company_name']:30} | {item['db_name']:30}\n"
                    f"    Expires: {item['expiry_date']} | {item['days_until_deletion']} days until deletion"
                )
            self.stdout.write("")
        
        if summary['deletion_eligible_companies']:
            self.stdout.write(self.style.ERROR("COMPANIES ELIGIBLE FOR DELETION:"))
            self.stdout.write("-" * 80)
            for item in summary['deletion_eligible_companies']:
                self.stdout.write(
                    f"  {item['company_name']:30} | {item['db_name']:30}\n"
                    f"    Expired: {item['expiry_date']} | {item['days_past_expiry']} days ago"
                )
            self.stdout.write("")
        
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))
        
        if not summary['grace_period_companies'] and not summary['deletion_eligible_companies']:
            self.stdout.write(self.style.SUCCESS("✓ No cleanup action required.\n"))

    def _show_summary(self):
        """Show detailed summary."""
        summary = get_cleanup_summary()
        
        self.stdout.write(self.style.SUCCESS("\nCLEANUP SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Generated: {summary['timestamp']}\n")
        
        self.stdout.write(f"Total Expired: {summary['total_expired']}")
        self.stdout.write(f"In Grace Period: {summary['in_grace_period']}")
        self.stdout.write(f"Eligible for Deletion: {summary['eligible_for_deletion']}\n")

    def _handle_export(self, options):
        """Export cleanup report."""
        export_format = options['export']
        
        try:
            report = export_cleanup_report(format=export_format)
            self.stdout.write(report)
        except Exception as e:
            raise CommandError(f"Failed to export report: {e}")

    def _handle_delete(self, options):
        """Handle manual company deletion."""
        company_id = options['delete']
        keep_entry = options.get('keep_entry', False)
        force = options.get('force', False)
        
        # Get detailed impact information
        from Lyraerp.utils.cleanup_utils import get_master_database_impact
        
        impact = get_master_database_impact(company_id)
        
        if 'error' in impact:
            self.stdout.write(self.style.ERROR(f"✗ {impact['error']}\n"))
            return
        
        # Show what will be deleted
        self.stdout.write(self.style.WARNING("\n⚠️  WARNING: You are about to delete the following:"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"\nCompany: {impact['company_name']} (ID: {impact['company_id']})")
        self.stdout.write(f"Database: {impact['db_name']}")
        self.stdout.write("\nMaster Database Records that will be CASCADE-DELETED:")
        self.stdout.write("-" * 80)
        
        if impact['related_data']:
            for record_type, count in impact['related_data'].items():
                self.stdout.write(f"  • {record_type}: {count}")
            self.stdout.write("")
        
        self.stdout.write(f"TOTAL Records to be deleted: {impact['total_records_to_delete']}")
        self.stdout.write("=" * 80)
        
        if not force:
            self.stdout.write(
                "The company will be checked for active licenses before deletion."
            )
        else:
            self.stdout.write(
                self.style.ERROR("FORCE MODE: Will delete even with active license!")
            )
        
        mode = "archived (records kept)" if keep_entry else "completely removed (records deleted)"
        self.stdout.write(f"Deletion mode: {self.style.WARNING(mode)}")
        
        # Confirmation prompt
        self.stdout.write("")
        confirm = input("Type 'DELETE' to confirm deletion, or press Enter to cancel: ")
        
        if confirm != 'DELETE':
            self.stdout.write(self.style.WARNING("❌ Deletion cancelled.\n"))
            return
        
        # Perform deletion
        result = manually_delete_company(
            company_id,
            remove_entry=not keep_entry,
            force=force,
        )
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"✓ {result['message']}\n"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ {result['message']}\n"))
