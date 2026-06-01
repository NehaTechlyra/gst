"""Import the full world location dataset used by the ERP company setup flow."""

from django.core.management import BaseCommand, CommandError, call_command
from django.db import OperationalError

from cities_light.models import City as WorldCity
from cities_light.models import Country as WorldCountry


class Command(BaseCommand):
    help = "Download and import the full world countries, regions, and cities dataset"

    def handle(self, *args, **kwargs):
        try:
            if WorldCountry.objects.exists() and WorldCity.objects.exists():
                self.stdout.write(
                    self.style.SUCCESS("World location data is already imported.")
                )
                return
        except OperationalError as exc:
            raise CommandError(
                "The cities_light tables are not ready yet. Run `python manage.py migrate` first."
            ) from exc

        self.stdout.write(
            "Importing the world dataset via django-cities-light. "
            "This can take a while the first time."
        )

        call_command("cities_light", force_import_all=True)

        self.stdout.write(
            self.style.SUCCESS(
                "World location data import finished. Countries, regions, and cities are now available."
            )
        )
