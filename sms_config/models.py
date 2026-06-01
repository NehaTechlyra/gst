from django.db import models
from django.conf import settings
from sms_templates.constants import SMS_TEMPLATE_NAME_CHOICES
from multiselectfield import MultiSelectField
import os

# Use thread-local helper to find the current company DB when available
from Lyraerp.utils.thread_locals import get_current_db


class SMSConfigurationManager(models.Manager):
    """Manager that routes queries to the active company database when present.

    Behavior:
    - If thread-local `company_db` is set and not 'default', use that DB.
    - Otherwise, check the `COMPANY_DB` environment variable or
      `settings.DEFAULT_COMPANY_DB` for a fallback when running outside
      of a request (e.g. manage.py shell).
    - Fall back to the default DB if no company DB is found.
    """
    def get_queryset(self):
        qs = super().get_queryset()

        # Respect explicit `.using('db')` on the manager (Django sets `_db`).
        manager_db = getattr(self, '_db', None)
        if manager_db and manager_db != 'default':
            return qs.using(manager_db)

        company_db = get_current_db()
        # If thread-local isn't set, try env or settings fallback
        if company_db == 'default':
            env_db = os.environ.get('COMPANY_DB') or getattr(settings, 'DEFAULT_COMPANY_DB', None)
            if env_db:
                company_db = env_db

        # SMSConfiguration lives only in company databases. Avoid accidentally
        # querying the master DB which doesn't have the table.
        if not company_db or company_db == 'default':
            raise RuntimeError(
                "SMSConfiguration queries require a company database context. "
                "Set the COMPANY_DB environment variable, define settings.DEFAULT_COMPANY_DB, "
                "use .using('company_db_name') on the queryset, or run inside a request with company context."
            )

        return qs.using(company_db)


class SMSConfiguration(models.Model):
    # Add custom manager as default
    objects = SMSConfigurationManager()

    MODE_CHOICES = [
        ("gsm", "GSM Modem"),
        ("mobile", "Mobile as Modem"),
        ("api", "Cloud API"),
    ]

    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="gsm")
    status = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    #  Hard-coded list, NOT database M2M field
    usage_types = MultiSelectField(
        choices=SMS_TEMPLATE_NAME_CHOICES,
        max_length=300,
        blank=True
    )


    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_config_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_config_updated'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SMS Configuration"
        verbose_name_plural = "SMS Configurations"

    def __str__(self):
        return f"{self.get_mode_display()} Configuration"

    def get_usage_types_display_list(self):
            """
            Returns human-readable usage type labels
            """
            if not self.usage_types:
                return []

            choices_dict = dict(self._meta.get_field("usage_types").choices)
            return [choices_dict.get(v, v) for v in self.usage_types]


# ─────────────────────────────────────────────
# GSM MODEM CONFIGURATION (ALLOW MULTIPLE)
# ─────────────────────────────────────────────
class GSMModemConfig(models.Model):
    sms_config = models.ForeignKey(
        SMSConfiguration,
        on_delete=models.CASCADE,
        related_name='gsm_configs'
    )
    gsm_port = models.CharField(max_length=50, blank=True, null=True)
    gsm_baudrate = models.PositiveIntegerField(blank=True, null=True)
    gsm_timeout = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"GSM Modem ({self.gsm_port or 'Unknown'})"


# ─────────────────────────────────────────────
# MOBILE AS MODEM CONFIGURATION
# ─────────────────────────────────────────────
class MobileModemConfig(models.Model):
    sms_config = models.ForeignKey(SMSConfiguration, related_name="mobile_configs", on_delete=models.CASCADE)
    mobile_port = models.CharField(max_length=100, default="")
    mobile_baudrate = models.IntegerField(default=9600, null=True, blank=True)
    mobile_timeout = models.IntegerField(default=5, null=True, blank=True)

    def __str__(self):
        return f"Mobile Port: {self.mobile_port}"



# ─────────────────────────────────────────────
# API CONFIGURATION
# ─────────────────────────────────────────────
class APIConfig(models.Model):
    sms_config = models.ForeignKey(
        SMSConfiguration,
        related_name="api_configs",
        on_delete=models.CASCADE
    )
    api_url = models.URLField(blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_sender = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"API: {self.api_url}"
