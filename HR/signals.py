from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import RecruitmentOffer
from .services import sync_candidate_with_offer


@receiver(pre_save, sender=RecruitmentOffer)
def _record_previous_offer_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = RecruitmentOffer.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except RecruitmentOffer.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=RecruitmentOffer)
def _sync_candidate_on_offer_save(sender, instance, created, **kwargs):
    if getattr(instance, '_skip_candidate_sync', False):
        return
    previous_status = getattr(instance, '_previous_status', None)
    if not created and previous_status == instance.status:
        return
    sync_candidate_with_offer(instance)
