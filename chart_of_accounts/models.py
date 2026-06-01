from django.db import models
from django.conf import settings

class ChartOfAccounts(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    
    type = models.CharField(max_length=25)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)
    is_header = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='accounts_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this brand"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='accounts_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this brand"
    )
    status = models.BooleanField(default=True)
    search_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional search code for quick lookup"
    )
    class Meta:
        db_table = 'chart_of_accounts'
        verbose_name_plural = "Chart of Accounts"

    def __str__(self):
        return f"{self.code} - {self.name}"


