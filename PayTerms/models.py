from django.db import models
from django.conf import settings

# Create your models here.
class PayTerms(models.Model):
    name = models.CharField(max_length=100)
    # description = models.TextField(blank=True, null=True, help_text="Optional detailed description of the payment term")
    days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='payterms_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this payment term"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='payterms_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this payment term"
    )
    def __str__(self):
        return f"{self.name} ({self.days} days)"