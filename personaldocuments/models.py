from django.db import models
from django.conf import settings
from django.utils.timezone import now  # <- add this import

class PersonalDocumentType(models.Model):
    """Stores predefined personal document types with example format"""
    name = models.CharField(max_length=150, unique=True)
    example_format = models.CharField(max_length=150, blank=True)

    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now, editable=False)  # existing rows get timestamp
    updated_at = models.DateTimeField(default=now)                 # existing rows get timestamp
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='personal_document_types_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='personal_document_types_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Personal Document Type"
        verbose_name_plural = "Personal Document Types"

    def __str__(self):
        return self.name
