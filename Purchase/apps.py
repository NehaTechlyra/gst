from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Purchase'

    def ready(self):
        import Purchase.signals
        import Purchase.serializer