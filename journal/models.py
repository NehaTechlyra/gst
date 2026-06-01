from django.db import models
from django.conf import settings
from chart_of_accounts.models import ChartOfAccounts

class JournalEntry(models.Model):
    """Main journal entry header"""
    entry_number = models.CharField(max_length=20, unique=True)
    date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    narration = models.TextField(blank=True)
    
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, default='draft', 
                            choices=[('draft', 'Draft'),
                                   ('posted', 'Posted'),
                                   ('cancelled', 'Cancelled')])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='journal_entries_created',
        on_delete=models.PROTECT
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='journal_entries_updated',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['-date', '-entry_number']

    def __str__(self):
        return f"{self.entry_number} - {self.date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save first to ensure we have a pk
        # Calculate totals for both new and existing entries
        if hasattr(self, 'lines'):  # Check if lines relation exists
            self.total_debit = sum(line.debit or 0 for line in self.lines.all())
            self.total_credit = sum(line.credit or 0 for line in self.lines.all())
            if self.total_debit != self.total_debit or self.total_credit != self.total_credit:
                super().save(*args, **kwargs)  # Save again if totals changed

    @property
    def description(self):
        """Return the first non-empty line description for display in lists."""
        first_line = self.lines.filter(description__isnull=False).exclude(description='').order_by('sequence').first()
        return first_line.description if first_line else ''

class JournalLine(models.Model):
    """Individual line items in a journal entry"""
    journal = models.ForeignKey(
        JournalEntry,
        related_name='lines',
        on_delete=models.CASCADE
    )
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='journal_lines'
    )
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sequence = models.IntegerField(default=10)
    status = models.BooleanField(default=True, help_text="Whether this journal line is active or deleted")

    class Meta:
        ordering = ['sequence']

    def __str__(self):
        return f"{self.journal.entry_number} - {self.account.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.debit != 0 and self.credit != 0:
            raise ValidationError('A line cannot have both debit and credit amounts')
        if self.debit == 0 and self.credit == 0:
            raise ValidationError('Either debit or credit amount must be non-zero')
