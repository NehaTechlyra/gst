from django.core.management.base import BaseCommand, CommandError

from company.models import Company
from Lyraerp.utils.db_utils import migrate_company_database


class Command(BaseCommand):
    help = "Run Django migrations on a single company (tenant) database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--db-name",
            dest="db_name",
            help="Tenant database name (e.g. lyra_mastertech6_acme_1_ab12cd).",
        )
        parser.add_argument(
            "--company-code",
            dest="company_code",
            help="Company code from URL (e.g. JPMORGAN-2026-YXV6). Looks up db_name in master DB.",
        )

    def handle(self, *args, **options):
        db_name = options.get("db_name")
        company_code = options.get("company_code")

        if bool(db_name) == bool(company_code):
            raise CommandError("Provide exactly one of --db-name or --company-code.")

        if company_code:
            company = Company.objects.using("default").filter(company_code=company_code).only("db_name").first()
            if not company or not company.db_name:
                raise CommandError(f"Company not found or db_name missing for company_code={company_code!r}.")
            db_name = company.db_name

        self.stdout.write(self.style.NOTICE(f"Migrating tenant database: {db_name}"))
        migrate_company_database(db_name)
        self.stdout.write(self.style.SUCCESS(f"Done: {db_name}"))

