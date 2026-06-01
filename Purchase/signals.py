from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import DeliveryNote

# @receiver(post_save, sender=DeliveryNote)
# def handle_delivery_status_change(sender, instance, created, **kwargs):
#     """
#     Automatically update stock when delivery status changes to 'delivered'
#     """
#     if instance.status == 'delivered' and not instance.stock_updated:
#         instance.update_stock()
#     elif instance.status == 'cancelled' and instance.stock_updated:
#         instance.reverse_stock()


@receiver(pre_save, sender=DeliveryNote)
def track_status_change(sender, instance, **kwargs):
    """
    Track status changes to handle stock updates
    """
    if instance.pk:
        try:
            old_instance = DeliveryNote.objects.get(pk=instance.pk)
            # Store old status for comparison
            instance._old_status = old_instance.status
        except DeliveryNote.DoesNotExist:
            instance._old_status = None