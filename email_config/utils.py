from django.core.mail import send_mail as django_send_mail
from django.core.mail import get_connection
from .models import EmailConfiguration

def get_active_email_configs():
    return EmailConfiguration.objects.filter(status=True).order_by('id')

import traceback

def send_email(recipient_list, subject=None, message=None, from_email=None, fail_silently=False):
    configs = get_active_email_configs()
    if not configs:
        raise Exception("No active email configuration found.")

    if isinstance(recipient_list, str):
        recipient_list = recipient_list.strip("[]").replace('"', '').replace("'", '').split(",")

    recipient_list = [email.strip() for email in recipient_list if email.strip()]
    last_exception = None

    for config in configs:
        try:
            connection = get_connection(
                host=config.host,
                port=config.port,
                username=config.host_user,
                password=config.host_password,
                use_tls=config.use_tls,
                fail_silently=fail_silently
            )

            final_subject = subject or config.email_subject or "Notification"
            final_message = message or config.email_message or ""
            actual_from = from_email or config.default_from_email or config.host_user

            if not actual_from:
                raise Exception("Default FROM email is missing in Email Configuration.")

            return django_send_mail(
                final_subject,
                "",
                actual_from,
                recipient_list,
                html_message=final_message,           # <-- IMPORTANT (HTML support)
                connection=connection,
                fail_silently=fail_silently
            )

        except Exception as e:
            print("------ EMAIL SEND ERROR TRACEBACK ------")
            traceback.print_exc()                   # <-- real server traceback
            print("---------------------------------------")
            last_exception = str(e)                # <-- store real string message
            continue

    raise Exception(f"All email configurations failed. Last error: {last_exception}")
