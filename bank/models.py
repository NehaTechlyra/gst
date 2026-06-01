from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

class Bank(models.Model):
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='banks_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this brand"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='banks_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this brand"
    )

    class Meta:
        ordering = ['bank_name']
        verbose_name = "bank"
        verbose_name_plural = "banks"

    def __str__(self):
        """Display the bank name in admin and dropdowns."""
        return self.bank_name or "Unnamed bank"


class BankReconciliation(models.Model):
    """Main bank reconciliation record - Zoho Books style with CSV import"""
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Reconciled', 'Reconciled'),
    ]
    
    bank_account = models.ForeignKey(
        'company_settings.CompanyBankAccount',
        on_delete=models.CASCADE,
        related_name='reconciliations',
        help_text="The bank account being reconciled"
    )
    
    # Period information
    start_date = models.DateField(
        help_text="Period start date"
    )
    end_date = models.DateField(
        help_text="Period end date"
    )
    
    # Balances
    closing_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Closing balance from bank statement"
    )
    
    cleared_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Sum of ticked/cleared transactions (auto-calculated)"
    )
    
    difference = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Difference = closing_balance - cleared_amount"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='In Progress',
        help_text="'In Progress' or 'Reconciled'"
    )
    
    # Attachment
    attachment = models.FileField(
        upload_to='bank_reconciliation_attachments/',
        blank=True,
        null=True,
        help_text="Optional bank statement or supporting document"
    )
    
    # Dates
    reconciled_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when reconciliation was completed"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reconciliations_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Bank Reconciliation'
        verbose_name_plural = 'Bank Reconciliations'
        ordering = ['-end_date']
        unique_together = ('bank_account', 'end_date')  # One reconciliation per period per account
    
    def __str__(self):
        return f"Reconciliation {self.bank_account} - {self.end_date}"
    
    def is_reconciled(self):
        """Check if reconciliation is complete"""
        return self.status == 'Reconciled'
    
    def is_locked(self):
        """Check if transactions in this reconciliation are locked"""
        return self.is_reconciled()
    
    @property
    def period_display(self):
        """Display period as 'start_date to end_date'"""
        return f"{self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}"
    
    def get_unmatched_statements(self):
        """Get unmatched bank statement entries"""
        return self.statement_lines.filter(match_status='unmatched')
    
    def get_cleared_lines(self):
        """Get all cleared transaction lines"""
        return self.lines.filter(is_cleared=True)


class BankRule(models.Model):
    """Persistent bank rule to help auto-matching statement lines.

    Example: rule to match 'PAYROLL' descriptions within +/-2 days and ₹5 tolerance.
    """
    bank_account = models.ForeignKey(
        'company_settings.CompanyBankAccount',
        on_delete=models.CASCADE,
        related_name='bank_rules',
        help_text='Bank account this rule applies to'
    )
    name = models.CharField(max_length=120)
    pattern = models.CharField(
        max_length=255,
        help_text='Regex or text fragment to match against statement description'
    )
    amount_tolerance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Amount tolerance when matching (absolute difference)'
    )
    date_window = models.IntegerField(
        default=0,
        help_text='Number of days before/after statement date to search for transactions'
    )
    active = models.BooleanField(default=True)
    auto_match = models.BooleanField(default=True, help_text='If true, apply this rule automatically')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bank Rule'
        verbose_name_plural = 'Bank Rules'

    def __str__(self):
        return f"{self.name} ({self.bank_account})"


class BankReconciliationLine(models.Model):
    """System transactions (cleared/matched in a reconciliation)"""
    TRANSACTION_TYPE_CHOICES = [
        ('payment_received', 'Payment Received'),
        ('payment_made', 'Payment Made'),
        ('journal', 'Journal Entry'),
        ('manual', 'Manual Adjustment'),
    ]
    
    reconciliation = models.ForeignKey(
        BankReconciliation,
        on_delete=models.CASCADE,
        related_name='lines',
        help_text="Parent reconciliation"
    )
    
    # Transaction reference
    transaction_id = models.IntegerField(
        help_text="ID of the transaction (journal_entry ID, payment ID, etc.)"
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPE_CHOICES,
        help_text="Type of transaction"
    )
    
    # Transaction details
    transaction_date = models.DateField(
        help_text="Date of the transaction"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description from the transaction"
    )
    
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference number (cheque #, invoice #, etc.)"
    )
    
    # Amount fields (debit/credit)
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Debit amount (outflow)"
    )
    
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Credit amount (inflow)"
    )
    
    # Reconciliation flags
    is_cleared = models.BooleanField(
        default=False,
        help_text="True = user ticked this transaction as cleared"
    )
    
    auto_matched = models.BooleanField(
        default=False,
        help_text="True = system auto-matched this to a statement line"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Reconciliation Line'
        verbose_name_plural = 'Reconciliation Lines'
        ordering = ['transaction_date']
        unique_together = ('reconciliation', 'transaction_id', 'transaction_type')
    
    def __str__(self):
        return f"{self.description} - Dr: {self.debit_amount}, Cr: {self.credit_amount}"
    
    @property
    def amount(self):
        """Signed amount: debit positive, credit negative.

        Returns a Decimal: debit_amount if present (>0), otherwise -credit_amount.
        """
        if self.debit_amount and self.debit_amount > 0:
            return self.debit_amount
        return -self.credit_amount if self.credit_amount else Decimal('0.00')


class BankStatementLine(models.Model):
    """Bank statement entries (from CSV upload)"""
    MATCH_STATUS_CHOICES = [
        ('auto_matched', 'Auto Matched'),
        ('manually_matched', 'Manually Matched'),
        ('unmatched', 'Unmatched'),
    ]
    
    bank_account = models.ForeignKey(
        'company_settings.CompanyBankAccount',
        on_delete=models.CASCADE,
        related_name='statement_lines',
        help_text="Bank account this statement line belongs to"
    )
    
    reconciliation = models.ForeignKey(
        BankReconciliation,
        on_delete=models.CASCADE,
        related_name='statement_lines',
        blank=True,
        null=True,
        help_text="Which reconciliation this was uploaded for"
    )
    
    # Statement details
    statement_date = models.DateField(
        help_text="Date of the transaction"
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Description from the bank statement"
    )
    
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference from bank statement"
    )
    
    # Amount fields (debit/credit)
    debit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Debit amount (outflow)"
    )
    
    credit_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Credit amount (inflow)"
    )
    
    # Matching
    matched_transaction_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID of matched system transaction (if any)"
    )
    
    match_status = models.CharField(
        max_length=20,
        choices=MATCH_STATUS_CHOICES,
        default='unmatched',
        help_text="Match status with system transactions"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Bank Statement Line'
        verbose_name_plural = 'Bank Statement Lines'
        ordering = ['statement_date']
        indexes = [
            models.Index(fields=['bank_account', 'statement_date']),
            models.Index(fields=['match_status']),
        ]
    
    def __str__(self):
        return f"{self.statement_date} - {self.description}"
    
    @property
    def amount(self):
        """Get total amount (debit or credit, whichever is non-zero)"""
        if self.debit_amount and self.debit_amount > 0:
            return self.debit_amount
        return -self.credit_amount if self.credit_amount else Decimal('0.00')

