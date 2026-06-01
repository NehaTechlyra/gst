from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Allowances(models.Model):
    allowances_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='allowances_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this brand"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='allowances_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this brand"
    )

    class Meta:
        ordering = ['allowances_name']
        verbose_name = "allowance"
        verbose_name_plural = "allowances"

    def __str__(self):
        """Show the allowance name clearly in admin and dropdowns."""
        return self.allowances_name or "Unnamed Allowance"

