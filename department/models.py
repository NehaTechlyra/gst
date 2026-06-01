from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Department(models.Model):
    department_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='departments_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this department"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='departments_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this department"
    )

    class Meta:
        ordering = ['department_name']
        verbose_name = "department"
        verbose_name_plural = "departments"

    def __str__(self):
        """Return department name in admin and dropdowns."""
        return self.department_name or "Unnamed Department"
