"""
Trial Management Utilities

Helper functions for:
- Sending trial reminder emails
- Sending trial expired emails
- Checking trial status
- Generating trial summary
"""

import logging
from datetime import datetime
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from company.utils import get_company_logo_base64

logger = logging.getLogger(__name__)


def send_trial_reminder_email(company):
    """
    Send 10-day trial reminder email.
    
    Args:
        company: Company instance
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Calculate days remaining
        days_left = company.days_until_trial_expires()
        
        if days_left is None:
            logger.warning(f"Cannot calculate trial days for {company.name}")
            return False
        
        # Email context
        context = {
            'company_name': company.name,
            'company_logo_base64': get_company_logo_base64(company),
            'contact_person': company.contact_person or 'Customer',
            'days_remaining': days_left,
            'trial_expires_at': company.trial_expires_at.strftime('%B %d, %Y'),
            'contact_email': 'lyraerp@techlyra.com',
            'login_url': f"{settings.BASE_URL}/{company.company_code}/",
        }
        
        # Render email template
        html_content = render_to_string('emails/trial_reminder.html', context)
        text_content = strip_tags(html_content)
        
        # Create email
        subject = f'Your Lyra ERP Trial Expires in {days_left} Days'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = company.contact_email or company.email
        
        if not to_email:
            logger.error(f"No email address for company {company.name}")
            return False
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        
        # Mark reminder as sent
        company.mark_trial_reminder_sent()
        
        logger.info(f"✅ Trial reminder sent to {company.name} ({to_email})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send trial reminder to {company.name}: {e}", exc_info=True)
        return False


def send_trial_expired_email(company):
    """
    Send trial expired email (sent daily until license activated).
    
    Args:
        company: Company instance
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Email context
        context = {
            'contact_person': company.contact_person or 'Customer',
            'trial_expired_date': company.trial_expires_at.strftime('%B %d, %Y'),
            'contact_email': 'lyraerp@techlyra.com',
            'company_code': company.company_code,
        }
        
        # Render email template
        html_content = render_to_string('emails/trial_expired.html', context)
        text_content = strip_tags(html_content)
        
        # Create email
        subject = 'Your Lyra ERP Trial Has Expired - License Required'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = company.contact_email or company.email
        
        if not to_email:
            logger.error(f"No email address for company {company.name}")
            return False
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        
        # Mark expired email as sent
        company.mark_trial_expired_email_sent()
        
        logger.info(f"✅ Trial expired email sent to {company.name} ({to_email})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send trial expired email to {company.name}: {e}", exc_info=True)
        return False


def get_trial_summary(company):
    """
    Get human-readable trial summary for a company.
    
    Args:
        company: Company instance
        
    Returns:
        dict: Trial summary with status, days remaining, etc.
    """
    summary = {
        'status': 'unknown',
        'days_remaining': None,
        'is_expired': False,
        'has_license': False,
        'message': ''
    }
    
    # Check license first
    if company.has_valid_license():
        summary['status'] = 'licensed'
        summary['has_license'] = True
        summary['message'] = 'Active License'
        return summary
    
    # Trial not started yet
    if not company.trial_started_at:
        summary['status'] = 'pending'
        summary['message'] = 'Trial will start on first login'
        return summary
    
    # Calculate days remaining
    days_left = company.days_until_trial_expires()
    
    if days_left is None:
        summary['status'] = 'error'
        summary['message'] = 'Unable to determine trial status'
        return summary
    
    summary['days_remaining'] = days_left
    
    # Trial expired
    if days_left < 0:
        summary['status'] = 'expired'
        summary['is_expired'] = True
        summary['message'] = f'Trial expired {abs(days_left)} days ago'
    # Trial active
    elif days_left == 0:
        summary['status'] = 'expires_today'
        summary['message'] = 'Trial expires today'
    elif days_left <= 5:
        summary['status'] = 'expiring_soon'
        summary['message'] = f'{days_left} days remaining'
    else:
        summary['status'] = 'active'
        summary['message'] = f'{days_left} days remaining'
    
    return summary


def process_trial_reminders():
    """
    Process all companies and send trial reminder emails.
    Called by management command (daily cron job).
    
    Returns:
        dict: Summary of emails sent
    """
    from company.models import Company
    
    summary = {
        'reminders_sent': 0,
        'expired_sent': 0,
        'errors': 0
    }
    
    # Get all companies in trial
    companies = Company.objects.filter(
        trial_active=True,
        trial_started_at__isnull=False
    )
    
    logger.info(f"Processing trial reminders for {companies.count()} companies...")
    
    for company in companies:
        try:
            # Send 10-day reminder
            if company.should_send_trial_reminder():
                if send_trial_reminder_email(company):
                    summary['reminders_sent'] += 1
            
            # Send trial expired email
            if company.should_send_trial_expired_email():
                if send_trial_expired_email(company):
                    summary['expired_sent'] += 1
                    
        except Exception as e:
            logger.error(f"Error processing company {company.name}: {e}")
            summary['errors'] += 1
    
    logger.info(
        f"Trial reminders complete: "
        f"{summary['reminders_sent']} reminders sent, "
        f"{summary['expired_sent']} expired emails sent, "
        f"{summary['errors']} errors"
    )
    
    return summary
