"""
Management command to update license expiry status at midnight.
This command should be run hourly via cron job.

SCHEDULE:
- If license expires on 25th → email sent on 26th at 12:00 AM
- If license expires on 25th and this command runs on 25th → warning email sent on 25th

Usage:
    python manage.py check_and_update_license_expiry
    
This will:
1. Check each license to see if we've passed the expiry date (today > expiry_date)
2. Update is_license_expired flag to True if expiry date has been passed
3. Send expiry emails at 12:00 AM on the day AFTER expiry
4. Send warning emails on the expiry date itself (before midnight)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from company_settings.models import LicenseKey
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check and update license expiry status at midnight'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting license expiry check...'))
        
        # Get all active licenses
        licenses = LicenseKey.objects.filter(is_active=True)
        updated_count = 0
        email_sent_count = 0

        for license_obj in licenses:
            try:
                if not license_obj.expiry_date:
                    continue

                now = timezone.now()
                today = now.date()
                tomorrow = today + timedelta(days=1)
                
                # Check if today is AFTER expiry_date (i.e., the day after expiry)
                # If expiry_date = 25th, mark as expired on 26th at midnight
                if today > license_obj.expiry_date and not license_obj.is_license_expired:
                    # License just expired at midnight on the day AFTER expiry_date
                    license_obj.is_license_expired = True
                    license_obj.save(update_fields=['is_license_expired'])
                    updated_count += 1
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f'✓ License {license_obj.license_key} marked as EXPIRED on {today}'
                        )
                    )
                    
                    # Send expiry notification email
                    try:
                        self._send_license_expired_email(license_obj)
                        email_sent_count += 1
                    except Exception as e:
                        logger.error(f'Failed to send expiry email for {license_obj.license_key}: {e}')
                        self.stdout.write(
                            self.style.ERROR(f'✗ Failed to send email for {license_obj.license_key}')
                        )
                
                # Also check for licenses that expire today (send warning for expiring today)
                if today == license_obj.expiry_date and not license_obj.is_license_expired:
                    try:
                        self._send_license_expiring_today_email(license_obj)
                    except Exception as e:
                        logger.error(f'Failed to send expiry warning email for {license_obj.license_key}: {e}')

            except Exception as e:
                logger.error(f'Error processing license {license_obj.license_key}: {e}')
                self.stdout.write(
                    self.style.ERROR(f'✗ Error processing license: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ License check completed:\n'
                f'  - {updated_count} license(s) marked as expired\n'
                f'  - {email_sent_count} notification email(s) sent'
            )
        )

    def _send_license_expired_email(self, license_obj):
        """Send license expired notification email"""
        from company.models import Company
        
        company = license_obj.company
        
        # Check if we've already sent email recently (once every 24 hours)
        if license_obj.license_expired_email_last_sent:
            time_since_last_email = timezone.now() - license_obj.license_expired_email_last_sent
            if time_since_last_email.total_seconds() < 86400:  # 24 hours
                logger.info(f'Skipping email for {license_obj.license_key}, already sent recently')
                return

        # Get company contact info
        recipient_email = company.email or company.contact_email
        if not recipient_email:
            logger.warning(f'No email address for company {company.name}')
            return

        # Render email template
        context = {
            'company_name': company.name,
            'license_expiry_date': license_obj.expiry_date.strftime('%B %d, %Y'),
            'license_key': license_obj.license_key[:10] + '...',
        }
        
        html_content = render_to_string('emails/license_expired.html', context)
        text_content = f"""
License Expired

Your license for {company.name} expired on {license_obj.expiry_date.strftime('%B %d, %Y')}.
Please renew your license to continue using the system.
"""
        
        email = EmailMultiAlternatives(
            subject=f'License Expired - {company.name}',
            body=text_content,
            from_email='noreply@lyraerp.com',
            to=[recipient_email]
        )
        email.attach_alternative(html_content, 'text/html')
        email.send()
        
        # Mark email as sent
        license_obj.mark_license_expired_email_sent()
        
        logger.info(f'License expired email sent to {recipient_email} for {company.name}')
        self.stdout.write(self.style.SUCCESS(f'  - Email sent to {recipient_email}'))

    def _send_license_expiring_today_email(self, license_obj):
        """Send warning email for licenses expiring today (before they actually expire at midnight)"""
        from company.models import Company
        
        company = license_obj.company
        recipient_email = company.email or company.contact_email
        
        if not recipient_email:
            return

        context = {
            'company_name': company.name,
            'license_expiry_date': license_obj.expiry_date.strftime('%B %d, %Y'),
        }
        
        # Simple text email for warning
        text_content = f"""
License Expiring Today

Your license for {company.name} expires today at midnight ({license_obj.expiry_date.strftime('%B %d, %Y')}).
Please renew your license to avoid service interruption.
The system will be locked after midnight.
"""
        
        email = EmailMultiAlternatives(
            subject=f'License Expiring Today - {company.name}',
            body=text_content,
            from_email='noreply@lyraerp.com',
            to=[recipient_email]
        )
        email.send()
        
        logger.info(f'License expiring today warning email sent to {recipient_email} for {company.name}')
