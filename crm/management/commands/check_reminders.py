from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from crm.models import FollowUp


class Command(BaseCommand):
    help = 'Check for pending follow-ups and mark reminders as sent'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Get pending follow-ups that need reminders
        pending_followups = FollowUp.objects.filter(
            status='Pending',
            reminder_sent=False
        )
        
        for followup in pending_followups:
            # Calculate reminder time based on interval
            reminder_time = followup.followup_date
            
            if followup.reminder_interval == '15min':
                reminder_time = followup.followup_date - timedelta(minutes=15)
            elif followup.reminder_interval == '1hour':
                reminder_time = followup.followup_date - timedelta(hours=1)
            elif followup.reminder_interval == '1day':
                reminder_time = followup.followup_date - timedelta(days=1)
            
            # If reminder time has passed, mark as sent
            if now >= reminder_time:
                followup.reminder_sent = True
                followup.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Reminder sent for follow-up: {followup.description} (ID: {followup.id})'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('Reminder check completed.'))

