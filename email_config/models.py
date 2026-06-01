from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField
from email_templates.constants import TEMPLATE_NAME_CHOICES
import os

# Use thread-local helper to find the current company DB when available
from Lyraerp.utils.thread_locals import get_current_db


class EmailConfigurationManager(models.Manager):
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

        # EmailConfiguration lives only in company databases. Avoid accidentally
        # querying the master DB which doesn't have the table.
        if not company_db or company_db == 'default':
            raise RuntimeError(
                "EmailConfiguration queries require a company database context. "
                "Set the COMPANY_DB environment variable, define settings.DEFAULT_COMPANY_DB, "
                "use .using('company_db_name') on the queryset, or run inside a request with company context."
            )

        return qs.using(company_db)

class EmailConfiguration(models.Model):
    # Add custom manager as default
    objects = EmailConfigurationManager()

    host = models.CharField(max_length=100)
    port = models.PositiveIntegerField(blank=True, null=True)
    use_tls = models.BooleanField(default=True)
    host_user = models.EmailField(blank=True, null=True)
    host_password = models.CharField(max_length=255, blank=True, null=True)
    default_from_email = models.EmailField(blank=True, null=True)

     # 🔥 Hard-coded list, NOT database M2M field
    usage_types = MultiSelectField(
        choices=TEMPLATE_NAME_CHOICES,
        max_length=300,
        blank=True
    )

    status = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='email_config_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='email_config_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configurations"

    def __str__(self):
        return f"Email Config ({self.host_user or self.host})"