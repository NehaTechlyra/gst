from django.apps import AppConfig


class CompanyDetailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'company'

    def ready(self):
            # Import signals to ensure they are registered when the app is ready
            from . import signals