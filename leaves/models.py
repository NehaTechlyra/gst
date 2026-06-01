from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Leaves(models.Model):
    leaves_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='leaves_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this brand"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='leaves_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this brand"
    )

    class Meta:
        ordering = ['leaves_name']
        verbose_name = "leave"
        verbose_name_plural = "leaves"

    def __str__(self):
        """Display the leave name in admin and dropdowns."""
        return self.leaves_name or "Unnamed Leave"

