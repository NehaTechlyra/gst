from django.apps import AppConfig


# class UserConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'user'
#     def ready(self):
#         from . import signals


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'
    def ready(self):
        # Import signal handlers to ensure they're connected when the app is ready
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid crashing app import if signals file has errors; log if needed
            pass
