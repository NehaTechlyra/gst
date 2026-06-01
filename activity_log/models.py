from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json

User = get_user_model()

class ActivityLog(models.Model):
    """
    Comprehensive activity logging for all models in the project.
    Tracks CREATE, UPDATE, DELETE operations with before/after values.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('SEND_EMAIL', 'Send Email'),
        ('PRINT', 'Print'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]

    # Who performed the action
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activity_logs'
    )
    
    # What was the action
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # What model was affected (using ContentType for flexibility)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Object representation (for when object is deleted)
    object_repr = models.CharField(max_length=255, blank=True)
    
    # Model name for easier filtering
    model_name = models.CharField(max_length=100, blank=True)
    
    # Details about the change
    description = models.TextField(blank=True)
    
    # Store the actual changes (JSON format)
    changes = models.JSONField(null=True, blank=True)
    
    # Before and after values for updates
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    # Additional metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Related objects (for tracking relationships)
    related_object_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_logs'
    )
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('related_object_type', 'related_object_id')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
        ]
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"

    @property
    def formatted_changes(self):
        """Return a human-readable version of changes."""
        if not self.changes:
            return {}
        
        formatted = {}
        for field, change in self.changes.items():
            if isinstance(change, dict) and 'old' in change and 'new' in change:
                formatted[field] = f"{change['old']} → {change['new']}"
            else:
                formatted[field] = change
        return formatted