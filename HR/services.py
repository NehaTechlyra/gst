from django.db import transaction

from .models import Candidate, CandidateStatusHistory


def update_candidate_status(candidate, new_status, user=None, remarks=''):
    old_status = candidate.current_status
    if old_status == new_status and not remarks:
        return

    candidate.current_status = new_status
    if remarks:
        candidate.remarks = remarks

    update_fields = ['current_status', 'updated_at']
    if remarks:
        update_fields.append('remarks')
    if user and getattr(user, 'is_authenticated', False):
        candidate.updated_by = user
        update_fields.append('updated_by')

    # Ensure unique fields order
    seen = set()
    ordered_fields = []
    for field in update_fields:
        if field not in seen:
            seen.add(field)
            ordered_fields.append(field)

    with transaction.atomic():
        candidate.save(update_fields=ordered_fields)
        CandidateStatusHistory.objects.create(
            candidate=candidate,
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
            changed_by=user if getattr(user, 'is_authenticated', False) else None,
        )


def sync_candidate_with_offer(offer, user=None, remarks=None):
    status_map = {
        'sent': 'offer_sent',
        'accepted': 'offer_accepted',
        'declined': 'offer_declined',
        'cancelled': 'offer_cancelled',
    }
    candidate_status = status_map.get(offer.status)
    if not candidate_status:
        return
    if remarks is None:
        remarks = f"Offer status updated to {offer.get_status_display()}."
    update_candidate_status(offer.candidate, candidate_status, user=user, remarks=remarks)
