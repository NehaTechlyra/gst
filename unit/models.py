from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Unit(models.Model):
    unit_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='units_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this unit"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='units_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this unit"
    )

    class Meta:
        ordering = ['unit_name']
        verbose_name = "Unit"
        verbose_name_plural = "Units"
    


