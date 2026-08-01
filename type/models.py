from django.db import models
from django.conf import settings


class Type(models.Model):
    type_name = models.CharField(max_length=150, blank=True, null=True)
    subcategory = models.ForeignKey(
        'category.Subcategory',
        on_delete=models.PROTECT,
        related_name='types',
        verbose_name='Subcategory',
    )
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='types_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='types_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['type_name']
        verbose_name = 'Type'
        verbose_name_plural = 'Types'

    def __str__(self):
        return self.type_name or ''
