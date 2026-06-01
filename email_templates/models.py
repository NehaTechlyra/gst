from django.db import models
from django.conf import settings
from email_templates.constants import TEMPLATE_NAME_CHOICES
import os

# Use thread-local helper to find the current company DB when available
from Lyraerp.utils.thread_locals import get_current_db


class EmailTemplateStyleManager(models.Manager):
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

        # EmailTemplateStyle lives only in company databases. Avoid accidentally
        # querying the master DB which doesn't have the table.
        if not company_db or company_db == 'default':
            raise RuntimeError(
                "EmailTemplateStyle queries require a company database context. "
                "Set the COMPANY_DB environment variable, define settings.DEFAULT_COMPANY_DB, "
                "use .using('company_db_name') on the queryset, or run inside a request with company context."
            )

        return qs.using(company_db)


class EmailTemplateStyle(models.Model):
    # Add custom manager as default
    objects = EmailTemplateStyleManager()

    #  Hard-coded template name list
    template_name = models.CharField(
        max_length=150,
        choices=TEMPLATE_NAME_CHOICES,
        default="-"       # <-- DEFAULT ADDED
    )
    
    style = models.CharField(max_length=100)
    subject = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    is_default = models.BooleanField(default=False)
    is_hardcoded = models.BooleanField(default=False) 

    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, related_name="style_created",
        on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, related_name="style_updated",
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['template_name', 'style']          # <-- FIXED
        unique_together = ('template_name', 'style')   # <-- FIXED

    def __str__(self):
        return f"{self.template_name} — {self.style}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        # Only manage DEFAULT per template_name
        styles = EmailTemplateStyle.objects.filter(template_name=self.template_name)

        if self.is_default:
            styles.exclude(id=self.id).update(is_default=False)

        elif creating and styles.count() == 1:
            self.is_default = True
            super().save(update_fields=['is_default'])

        elif not styles.filter(is_default=True).exists():
            first_style = styles.first()
            first_style.is_default = True
            first_style.save(update_fields=['is_default'])

    def delete(self, *args, **kwargs):
        template_name = self.template_name
        was_default = self.is_default

        super().delete(*args, **kwargs)

        if was_default:
            next_style = EmailTemplateStyle.objects.filter(template_name=template_name).first()
            if next_style:
                next_style.is_default = True
                next_style.save(update_fields=['is_default'])
