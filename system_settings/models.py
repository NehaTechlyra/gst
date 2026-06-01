from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

class FiscalYear(models.Model):
    """
    Fiscal Year definition for period locking.
    Represents an accounting period (e.g., FY 2025-26: Apr 01, 2025 - Mar 31, 2026)
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Fiscal Year name (e.g. FY 2025-26)"
    )
    
    start_date = models.DateField(
        help_text="Fiscal year start date (e.g., 01 Apr 2025)"
    )
    
    end_date = models.DateField(
        help_text="Fiscal year end date (e.g., 31 Mar 2026)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Active = Current FY | Closed = Locked from edits | Archived = Historical"
    )
    
    is_locked = models.BooleanField(
        default=False,
        help_text="🔒 When TRUE: Prevents ALL edits (bills, items, journals, stock). View-only mode."
    )

    lock_items = models.BooleanField(
        default=False,
        help_text="Lock item master records for this fiscal year"
    )
    lock_stock = models.BooleanField(
        default=False,
        help_text="Lock stock transactions for this fiscal year"
    )
    lock_invoices = models.BooleanField(
        default=False,
        help_text="Lock invoice transactions for this fiscal year"
    )
    lock_bills = models.BooleanField(
        default=False,
        help_text="Lock bill transactions for this fiscal year"
    )
    lock_payments = models.BooleanField(
        default=False,
        help_text="Lock payment transactions for this fiscal year"
    )
    lock_journals = models.BooleanField(
        default=False,
        help_text="Lock journal entries for this fiscal year"
    )
    lock_expenses = models.BooleanField(
        default=False,
        help_text="Lock expense entries for this fiscal year"
    )
    lock_sales_return = models.BooleanField(
        default=False,
        help_text="Lock sales return transactions for this fiscal year"
    )
    lock_purchase_return = models.BooleanField(
        default=False,
        help_text="Lock purchase return transactions for this fiscal year"
    )
    lock_sales_delivery = models.BooleanField(
        default=False,
        help_text="Lock sales delivery note transactions for this fiscal year"
    )
    lock_purchase_delivery = models.BooleanField(
        default=False,
        help_text="Lock purchase delivery note transactions for this fiscal year"
    )
    
    lock_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was this fiscal year locked?"
    )
    
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_fiscal_years',
        help_text="User who locked this fiscal year"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fiscal_years_created'
    )
    
    class Meta:
        db_table = 'system_settings_fiscalyear'
        ordering = ['-start_date']
        verbose_name = 'Fiscal Year'
        verbose_name_plural = 'Fiscal Years'
        indexes = [
            models.Index(fields=['-start_date']),
            models.Index(fields=['is_locked']),
        ]
    
    def __str__(self):
        return f"{self.name} ({'🔒 LOCKED' if self.is_locked else 'OPEN'})"
    
    def clean(self):
        """Validate fiscal year dates"""
        if self.start_date >= self.end_date:
            raise ValidationError('Start date must be before end date.')
        
        # Check for overlapping fiscal years (excluding itself)
        overlapping = FiscalYear.objects.filter(
            models.Q(start_date__lte=self.end_date) & 
            models.Q(end_date__gte=self.start_date)
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError('This fiscal year overlaps with an existing fiscal year.')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    LOCK_CATEGORIES = {
        'items': 'lock_items',
        'stock': 'lock_stock',
        'invoice': 'lock_invoices',
        'bill': 'lock_bills',
        'payment': 'lock_payments',
        'journal': 'lock_journals',
        'expense': 'lock_expenses',
        'sales_return': 'lock_sales_return',
        'purchase_return': 'lock_purchase_return',
        'sales_delivery': 'lock_sales_delivery',
        'purchase_delivery': 'lock_purchase_delivery',
    }

    @property
    def locked_categories(self):
        return [k for k, f in self.LOCK_CATEGORIES.items() if getattr(self, f)]

    def _update_overall_lock_state(self):
        # if all individual categories are locked, keep is_locked True (full lock)
        if all(getattr(self, f) for f in self.LOCK_CATEGORIES.values()):
            self.is_locked = True
        else:
            # if manual is_locked set, preserve it; if not, keep false (partial lock)
            self.is_locked = self.is_locked and all(getattr(self, f) for f in self.LOCK_CATEGORIES.values())

    def lock(self, user=None, categories=None):
        """Lock this fiscal year (prevent edits). Support specific categories."""
        self.locked_by = user
        self.lock_date = timezone.now()

        if categories is None or 'all' in categories:
            # lock everything
            for attr in self.LOCK_CATEGORIES.values():
                setattr(self, attr, True)
            self.is_locked = True
        else:
            categories = set(categories)
            for category, attr in self.LOCK_CATEGORIES.items():
                if category in categories:
                    setattr(self, attr, True)

            # overall locked only when all categories are locked
            self._update_overall_lock_state()

        self.save(update_fields=['is_locked', 'lock_date', 'locked_by'] + list(self.LOCK_CATEGORIES.values()))

    def unlock(self, categories=None):
        """Unlock this fiscal year (allow edits). Support specific categories."""
        if categories is None or 'all' in categories:
            # unlock everything
            for attr in self.LOCK_CATEGORIES.values():
                setattr(self, attr, False)
            self.is_locked = False
        else:
            categories = set(categories)
            for category, attr in self.LOCK_CATEGORIES.items():
                if category in categories:
                    setattr(self, attr, False)
            # if all individual flags are false, unlock fully
            if not any(getattr(self, f) for f in self.LOCK_CATEGORIES.values()):
                self.is_locked = False

        self.lock_date = None if not self.is_locked else self.lock_date
        self.locked_by = None if not self.is_locked else self.locked_by

        self.save(update_fields=['is_locked', 'lock_date', 'locked_by'] + list(self.LOCK_CATEGORIES.values()))
    
    @property
    def is_current(self):
        """Check if this fiscal year is currently active"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def get_lock_status(self):
        """Returns human-readable lock status"""
        if self.is_locked:
            return f"🔒 LOCKED on {self.lock_date.strftime('%d %b %Y')} by {self.locked_by}"
        elif self.locked_categories:
            return f"🔒 PARTIAL LOCK ({', '.join(self.locked_categories)})"
        return "🔓 OPEN"


class PeriodLock(models.Model):
    """
    Audit log for period lock/unlock operations.
    Tracks who locked/unlocked periods and when.
    """
    ACTION_CHOICES = [
        ('lock', 'Locked'),
        ('unlock', 'Unlocked'),
    ]
    
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name='lock_history'
    )
    
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        help_text="Action performed: Lock or Unlock"
    )
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='period_lock_actions'
    )
    
    performed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When was this action performed?"
    )
    
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Why was this period locked/unlocked?"
    )

    categories = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated lock categories (items,stock,invoice,bill,payment,journal,expense,all)"
    )
    
    class Meta:
        db_table = 'system_settings_periodlock'
        ordering = ['-performed_at']
        verbose_name = 'Period Lock History'
        verbose_name_plural = 'Period Lock Histories'
    
    def __str__(self):
        return f"{self.fiscal_year.name} - {self.action.upper()} on {self.performed_at.strftime('%d %b %Y')}"


class PeriodLockExemption(models.Model):
    """
    Exemptions from period locking.
    Allows specific users to edit locked periods (e.g., auditors, superusers)
    """
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name='exemptions'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='period_lock_exemptions'
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Why is this user exempted from period locking?"
    )
    
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='period_exemptions_granted'
    )
    
    class Meta:
        db_table = 'system_settings_periodlockexemption'
        unique_together = ('fiscal_year', 'user')
        verbose_name = 'Period Lock Exemption'
        verbose_name_plural = 'Period Lock Exemptions'
    
    def __str__(self):
        return f"{self.user.username} - {self.fiscal_year.name}"

class BackupSchedule(models.Model):
    FREQUENCY_DAILY = 'daily'
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_MONTHLY = 'monthly'
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, 'Daily'),
        (FREQUENCY_WEEKLY, 'Weekly'),
        (FREQUENCY_MONTHLY, 'Monthly'),
    ]

    WEEKDAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    is_enabled = models.BooleanField(default=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=FREQUENCY_DAILY)
    run_time = models.TimeField(default='01:00')
    weekday = models.CharField(max_length=10, choices=WEEKDAY_CHOICES, blank=True, default='')
    month_day = models.PositiveSmallIntegerField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings_backupschedule'
        verbose_name = 'Backup Schedule'
        verbose_name_plural = 'Backup Schedules'

    def clean(self):
        if self.frequency == self.FREQUENCY_WEEKLY and not self.weekday:
            raise ValidationError('Weekday is required for weekly backup frequency.')
        if self.frequency == self.FREQUENCY_MONTHLY:
            if self.month_day is None:
                raise ValidationError('Date of month is required for monthly backup frequency.')
            if not 1 <= self.month_day <= 31:
                raise ValidationError('Date of month must be between 1 and 31.')

    def __str__(self):
        status = 'Enabled' if self.is_enabled else 'Disabled'
        return f"{status} - {self.frequency}"

class FiscalYearClosing(models.Model):
    """
    Tracks fiscal year closing entries.
    When a year is closed, income/expense accounts are zeroed out and 
    the net profit is transferred to retained earnings.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    fiscal_year = models.OneToOneField(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name='closing_record',
        help_text="The fiscal year being closed"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status of the closing process"
    )
    
    # Closing Entry References
    closing_journal_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID of the closing journal entry created during year-end"
    )
    
    opening_journal_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID of the opening balances journal entry for next FY"
    )
    
    # Financial Summary
    total_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total income for the fiscal year"
    )
    
    total_expenses = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total expenses for the fiscal year"
    )
    
    net_profit_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Net profit (if positive) or loss (if negative)"
    )
    
    # Audit Trail
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fiscal_closings_initiated'
    )
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fiscal_closings_completed'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was the closing completed?"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Notes about the closing process"
    )
    
    class Meta:
        db_table = 'system_settings_fiscalyearclosing'
        verbose_name = 'Fiscal Year Closing'
        verbose_name_plural = 'Fiscal Year Closings'
    
    def __str__(self):
        return f"{self.fiscal_year.name} - {self.status}"
