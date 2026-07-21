from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q

class Warehouse(models.Model):
    warehouse_name = models.CharField(max_length=100, blank=False, null=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Unique warehouse code")  # Identification field
    status = models.BooleanField(default=True)
    address = models.TextField(blank=False, null=True, help_text="Warehouse physical address")
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True, null=True, help_text="Additional details")
    warehouse_incharge = models.CharField(max_length=100, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='warehouses_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this warehouse"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='warehouses_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this warehouse"
    )

    def save(self, *args, **kwargs):
        # Extract the 'using' parameter to ensure queries use the correct database
        using = kwargs.get('using') or 'default'
        if self.is_default:
            # Make all other warehouses non-default
            Warehouse.objects.using(using).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_default:
            raise ValidationError("Default warehouse cannot be deleted")
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['warehouse_name']
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=Q(is_default=True),
                name='only_one_default_warehouse'
            )
        ]

    def __str__(self):
        return self.warehouse_name or f"Warehouse {self.pk}"




