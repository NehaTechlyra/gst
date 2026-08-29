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

    def handle(self, *args, **options):
        result = delete_expired_trial_databases_job(dry_run=options["dry_run"])
        action = "eligible" if options["dry_run"] else "deleted"
        self.stdout.write(
            self.style.SUCCESS(
                f"Trial/license database cleanup complete: "
                f"{result['deleted']} {action}, "
                f"{result['skipped']} skipped, "
                f"{result['errors']} errors"
            )
        )