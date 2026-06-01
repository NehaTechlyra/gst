from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from department.models import Department


class Designations(models.Model):
    departments = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='designations'
    )
    designation_name = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='designation_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this designation"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='designation_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this designation"
    )

    class Meta:
        ordering = ['designation_name']
        verbose_name = "designation"
        verbose_name_plural = "designations"

    def __str__(self):
        """Show department + designation name in admin or dropdown."""
        if self.departments:
            return f"{self.designation_name} ({self.departments.department_name})"
        return self.designation_name or "Unnamed Designation"
