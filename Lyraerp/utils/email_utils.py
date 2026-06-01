"""
Email utilities for Lyra ERP
All email content is driven by HTML templates — no hardcoded strings.

Template locations:
    templates/emails/registration_complete.html
    templates/emails/trial_reminder.html
    templates/emails/trial_expired.html
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

from company.utils import get_company_logo_base64

logger = logging.getLogger(__name__)

def _render_email(template_path, context):
    """
    Render an HTML email template.
    Returns (html_message, plain_message) tuple.
    Raises if the template is missing so the caller can log and bail out.
    """
    html_message = render_to_string(template_path, context)
    plain_message = strip_tags(html_message)
    return html_message, plain_message


def send_registration_email(company, user_email, username):
    """
    Send registration completion email with the unique login URL.

    Template: emails/registration_complete.html

    Context variables available in the template:
        {{ company_name }}   - Company name
        {{ username }}       - User's login username
        {{ company_code }}   - Unique company code
        {{ login_url }}      - Direct login URL for this company
        {{ base_url }}       - Base URL of the application
        {{ contact_email }}  - Support / from email address

    Args:
        company:    Company instance with company_code set
        user_email: Recipient email address
        username:   User's username

    Returns:
        bool: True if sent successfully, False otherwise
    """
    logger.info(f"[EMAIL] Sending registration email to {company.name} ({user_email})")
    try:
        # ──────────────────────────────────────────────────────────────
        # Step 1: Build email context
        # ──────────────────────────────────────────────────────────────
        try:
            context = {
                'company_name': company.name,
                'company_logo_base64': get_company_logo_base64(company),
                'username': username,
                'company_code': company.company_code,
                'login_url': f"{settings.BASE_URL}/login/{company.company_code}/",
                'base_url': settings.BASE_URL,
                'contact_email': settings.DEFAULT_FROM_EMAIL,
            }
            logger.debug(f"[EMAIL] Context built for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error building email context: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 2: Render email template
        # ──────────────────────────────────────────────────────────────
        try:
            html_message, plain_message = _render_email(
                'emails/registration_complete.html', context
            )
            logger.debug(f"[EMAIL] Template rendered successfully for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error rendering template 'emails/registration_complete.html': {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 3: Send email via SMTP
        # ──────────────────────────────────────────────────────────────
        try:
            subject = f"Welcome to Lyra ERP - {company.name}"
            logger.debug(f"[EMAIL] Sending to {user_email} with subject: {subject}")
            logger.debug(f"[EMAIL] EMAIL_HOST: {settings.EMAIL_HOST}")
            logger.debug(f"[EMAIL] EMAIL_PORT: {settings.EMAIL_PORT}")
            logger.debug(f"[EMAIL] EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.debug(f"[EMAIL] SMTP send_mail() completed for {user_email}")
        except Exception as e:
            logger.error(f"[EMAIL] Error sending email via SMTP to {user_email}: {e}", exc_info=True)
            raise

        logger.info(f"[OK] Registration email sent to {user_email} for {company.name}")
        return True

    except Exception as e:
        logger.error(
            f"[FAIL] Failed to send registration email to {user_email} "
            f"(company: {company.name}): {e}",
            exc_info=True,
        )
        return False


def send_trial_reminder_email(company, user_email):
    """
    Send a reminder that the trial is ending soon.
    Triggered on day 10 of the trial (5 days before expiry).
    Calls company.mark_trial_reminder_sent() on success.

    Template: emails/trial_reminder.html

    Context variables available in the template:
        {{ company_name }}    - Company name
        {{ contact_person }}  - Primary contact name
        {{ contact_email }}   - Support / from email address
        {{ login_url }}       - Direct login URL for this company
        {{ company_code }}    - Unique company code
        {{ days_remaining }}  - Integer days left before expiry
        {{ trial_expires_at}} - Formatted expiry date string e.g. "March 01, 2025"

    Args:
        company:    Company instance with trial fields populated
        user_email: Recipient email address

    Returns:
        bool: True if sent successfully, False otherwise
    """
    logger.info(f"[EMAIL] Sending trial reminder to {company.name} ({user_email})")
    try:
        # ──────────────────────────────────────────────────────────────
        # Step 1: Calculate days remaining
        # ──────────────────────────────────────────────────────────────
        try:
            days_remaining = company.days_until_trial_expires() or 5
            logger.debug(f"[EMAIL] Days remaining for {company.name}: {days_remaining}")
        except Exception as e:
            logger.error(f"[EMAIL] Error calculating days_remaining: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 2: Build email context
        # ──────────────────────────────────────────────────────────────
        try:
            context = {
                'company_name': company.name,
                'company_logo_base64': get_company_logo_base64(company),
                'contact_person': company.contact_person or company.name,
                'contact_email': settings.DEFAULT_FROM_EMAIL,
                'login_url': f"{settings.BASE_URL}/login/{company.company_code}/",
                'company_code': company.company_code,
                'days_remaining': days_remaining,
                'trial_expires_at': (
                    company.trial_expires_at.strftime('%B %d, %Y')
                    if company.trial_expires_at else 'soon'
                ),
            }
            logger.debug(f"[EMAIL] Context built for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error building email context: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 3: Render email template
        # ──────────────────────────────────────────────────────────────
        try:
            html_message, plain_message = _render_email(
                'emails/trial_reminder.html', context
            )
            logger.debug(f"[EMAIL] Template rendered successfully for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error rendering template 'emails/trial_reminder.html': {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 4: Send email via SMTP
        # ──────────────────────────────────────────────────────────────
        try:
            subject = (
                f"Your Lyra ERP Trial Expires in "
                f"{days_remaining} Day{'s' if days_remaining != 1 else ''} - {company.name}"
            )
            logger.debug(f"[EMAIL] Sending to {user_email} with subject: {subject}")
            logger.debug(f"[EMAIL] EMAIL_HOST: {settings.EMAIL_HOST}")
            logger.debug(f"[EMAIL] EMAIL_PORT: {settings.EMAIL_PORT}")
            logger.debug(f"[EMAIL] EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.debug(f"[EMAIL] SMTP send_mail() completed for {user_email}")
        except Exception as e:
            logger.error(f"[EMAIL] Error sending email via SMTP to {user_email}: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 5: Mark trial reminder as sent
        # ──────────────────────────────────────────────────────────────
        try:
            company.mark_trial_reminder_sent()
            logger.debug(f"[EMAIL] Marked trial_reminder_sent for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error marking trial reminder as sent: {e}", exc_info=True)
            raise

        logger.info(
            f"[OK] Trial reminder email sent to {user_email} "
            f"for {company.name} ({days_remaining} days left)"
        )
        return True

    except Exception as e:
        logger.error(
            f"[FAIL] Failed to send trial reminder email to {user_email} "
            f"(company: {company.name}): {e}",
            exc_info=True,
        )
        return False



def send_trial_expired_email(company, user_email):
    """
    Send a daily notification that the trial has expired and access is restricted.
    Called by the management command each day until a license is activated.
    Calls company.mark_trial_expired_email_sent() on success.

    Template: emails/trial_expired.html

    Context variables available in the template:
        {{ company_name }}       - Company name
        {{ contact_person }}     - Primary contact name
        {{ contact_email }}      - Support / from email address
        {{ company_code }}       - Unique company code
        {{ trial_expired_date }} - Formatted expiry date string e.g. "March 01, 2025"

    Args:
        company:    Company instance with trial fields populated
        user_email: Recipient email address

    Returns:
        bool: True if sent successfully, False otherwise
    """
    logger.info(f"[EMAIL] Sending trial expired email to {company.name} ({user_email})")
    try:
        # ──────────────────────────────────────────────────────────────
        # Step 1: Build email context
        # ──────────────────────────────────────────────────────────────
        try:
            context = {
                'contact_person': company.contact_person or company.name,
                'contact_email': settings.DEFAULT_FROM_EMAIL,
                'company_code': company.company_code,
                'trial_expired_date': (
                    company.trial_expires_at.strftime('%B %d, %Y')
                    if company.trial_expires_at else 'your trial period'
                ),
            }
            logger.debug(f"[EMAIL] Context built for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error building email context: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 2: Render email template
        # ──────────────────────────────────────────────────────────────
        try:
            html_message, plain_message = _render_email(
                'emails/trial_expired.html', context
            )
            logger.debug(f"[EMAIL] Template rendered successfully for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error rendering template 'emails/trial_expired.html': {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 3: Send email via SMTP
        # ──────────────────────────────────────────────────────────────
        try:
            subject = "Your Lyra ERP Trial Has Expired - License Required"
            logger.debug(f"[EMAIL] Sending to {user_email} with subject: {subject}")
            logger.debug(f"[EMAIL] EMAIL_HOST: {settings.EMAIL_HOST}")
            logger.debug(f"[EMAIL] EMAIL_PORT: {settings.EMAIL_PORT}")
            logger.debug(f"[EMAIL] EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.debug(f"[EMAIL] SMTP send_mail() completed for {user_email}")
        except Exception as e:
            logger.error(f"[EMAIL] Error sending email via SMTP to {user_email}: {e}", exc_info=True)
            raise

        # ──────────────────────────────────────────────────────────────
        # Step 4: Mark trial expired email as sent
        # ──────────────────────────────────────────────────────────────
        try:
            company.mark_trial_expired_email_sent()
            logger.debug(f"[EMAIL] Marked trial_expired_email_sent for {company.name}")
        except Exception as e:
            logger.error(f"[EMAIL] Error marking trial expired email as sent: {e}", exc_info=True)
            raise

        logger.info(f"[OK] Trial expired email sent to {user_email} for {company.name}")
        return True
    except Exception as e:
        logger.error(
            f"[FAIL] Failed to send trial expired email to {user_email} "
            f"(company: {company.name}): {e}",
            exc_info=True,
        )
        return False


def send_license_expired_email(license_obj, user_email):
    """
    Send a notification that the company's license has expired.
    Sends a single notification on the day AFTER expiry and then
    repeats every 72 hours until a valid license is activated.

    Template: emails/license_expired.html

    Args:
        license_obj: LicenseKey instance
        user_email: Recipient email address

    Returns:
        bool
    """
    company = getattr(license_obj, 'company', None)
    company_name = company.name if company else 'Your Company'
    logger.info(f"[EMAIL] Sending license expired email to {company_name} ({user_email})")
    try:
        from django.utils import timezone

        context = {
            'contact_person': company.contact_person if company and getattr(company, 'contact_person', None) else company_name,
            'contact_email': settings.DEFAULT_FROM_EMAIL,
            'license_expiry_date': (
                license_obj.expiry_date.strftime('%B %d, %Y') if license_obj.expiry_date else 'recently'
            ),
        }

        html_message, plain_message = _render_email('emails/license_expired.html', context)

        subject = "Your Lyra ERP License Has Expired"
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )

        # Mark sent on license object
        try:
            license_obj.mark_license_expired_email_sent()
        except Exception:
            logger.exception("Failed to mark license expired email as sent")

        logger.info(f"[OK] License expired email sent to {user_email} for {company_name}")
        return True
    except Exception as e:
        logger.error(f"[FAIL] Failed to send license expired email to {user_email}: {e}", exc_info=True)
        return False
