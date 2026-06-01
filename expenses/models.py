from django.db import models
from django.conf import settings
from django.utils import timezone
from chart_of_accounts.models import ChartOfAccounts
# Import the Tax model from the Tax app
from Tax.models import Tax


class Currency(models.Model):
    """Master table for currencies so they can be managed at runtime."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['code']

    def __str__(self):
        # Display as 'CODE - Name' (e.g. INR - Indian Rupee)
        return f"{self.code} - {self.name}"


PAID_THROUGH_CHOICES = [
    ('cash', 'Cash'),
    ('bank', 'Bank'),
    ('upi', 'UPI'),
]

EXPENSE_TYPE_CHOICES = [
    ('goods', 'Goods'),
    ('services', 'Services'),
]

GST_TREATMENT_CHOICES = [
    ('registered_regular', 'Registered Business - Regular'),
    ('registered_composition', 'Registered Business - Composition'),
    ('unregistered', 'Unregistered Business'),
    ('consumer', 'Consumer'),
    ('overseas', 'Overseas'),
    ('sez', 'Special Economic Zone'),
    ('deemed_export', 'Deemed Export'),
    ('non_gst', 'Non-GST Supply'),
    ('out_of_scope', 'Out Of Scope'),
    ('tax_deductor', 'Tax Deductor'),
    ('sez_developer', 'SEZ Developer'),
    ('input_service_distributor', 'Input Service Distributor'),
]

AMOUNT_IS_CHOICES = [
    ('inclusive', 'Tax Inclusive'),
    ('exclusive', 'Tax Exclusive'),
]

STATE_CHOICES = [
    ('AN', 'Andaman and Nicobar Islands'),
    ('AP', 'Andhra Pradesh'),
    ('AR', 'Arunachal Pradesh'),
    ('AS', 'Assam'),
    ('BR', 'Bihar'),
    ('CH', 'Chandigarh'),
    ('CT', 'Chhattisgarh'),
    ('DN', 'Dadra and Nagar Haveli'),
    ('DD', 'Daman and Diu'),
    ('DL', 'Delhi'),
    ('GA', 'Goa'),
    ('GJ', 'Gujarat'),
    ('HR', 'Haryana'),
    ('HP', 'Himachal Pradesh'),
    ('JK', 'Jammu and Kashmir'),
    ('JH', 'Jharkhand'),
    ('KA', 'Karnataka'),
    ('KL', 'Kerala'),
    ('LD', 'Lakshadweep'),
    ('MP', 'Madhya Pradesh'),
    ('MH', 'Maharashtra'),
    ('MN', 'Manipur'),
    ('ML', 'Meghalaya'),
    ('MZ', 'Mizoram'),
    ('NL', 'Nagaland'),
    ('OR', 'Odisha'),
    ('PY', 'Puducherry'),
    ('PB', 'Punjab'),
    ('RJ', 'Rajasthan'),
    ('SK', 'Sikkim'),
    ('TN', 'Tamil Nadu'),
    ('TG', 'Telangana'),
    ('TR', 'Tripura'),
    ('UP', 'Uttar Pradesh'),
    ('UT', 'Uttarakhand'),
    ('WB', 'West Bengal'),
]

class Vendor(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Expense(models.Model):
    date = models.DateField(default=timezone.now)
    # Store currency as a short code (e.g. 'INR', 'USD', 'AED').
    # Choices are populated dynamically in the form from the Currency master table,
    # so keep the model field free of hard-coded choices to allow runtime-managed currencies.
    currency = models.CharField(max_length=10, default='INR')
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=1.000000,
        help_text='Exchange rate from expense currency to company base currency.',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=0.00, max_digits=18, decimal_places=2)
    status = models.BooleanField(default=True, help_text="Whether this expense is active or deleted")

    # Payment and vendor info
    paid_through = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='expense_payments')
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES, default='services')
    sac_hsn = models.CharField(max_length=50, blank=True)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name='expenses')

    # GST / supply info
    gst_treatment = models.CharField(max_length=30, choices=GST_TREATMENT_CHOICES, default='registered_regular')
    place_of_supply = models.CharField(max_length=100, choices=[(state[1], state[1]) for state in STATE_CHOICES], blank=True, help_text='State where supply originates')
    destination_of_supply = models.CharField(max_length=100, choices=[(state[1], state[1]) for state in STATE_CHOICES], blank=True, help_text='State where supply is consumed')
    reverse_charge = models.BooleanField(default=False)
    amount_is = models.CharField(max_length=20, choices=AMOUNT_IS_CHOICES, default='exclusive')

    # Additional details
    invoice_number = models.CharField(max_length=100, blank=True)
    customer = models.CharField(max_length=255, blank=True)
    vendor_gstin = models.CharField(max_length=15, blank=True, verbose_name="Vendor GSTIN",
                                  help_text="15-digit GST Identification Number")

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Expense {self.pk} - {self.date} - {self.total_amount} {self.currency}"

    @property
    def subtotal(self):
        """Sum of all expense lines' amounts (before tax)"""
        return sum(float(line.amount) for line in self.lines.all())

    @property
    def tax_amount(self):
        """Sum of all expense lines' tax amounts"""
        return sum(line.tax_amount for line in self.lines.all())

    @property
    def total_amount(self):
        """Sum of all expense lines' total amounts (including tax)"""
        return sum(line.total_amount for line in self.lines.all())


def get_default_expense_account():
    """Get the first available expense account's ID"""
    try:
        account = ChartOfAccounts.objects.filter(type='4', is_header=False).first()
        return account.id if account else None
    except:
        return None

class ExpenseLine(models.Model):
    expense = models.ForeignKey(Expense, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='expense_lines',
        default=get_default_expense_account
    )
    notes = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.BooleanField(default=True, help_text="Whether this expense line is active or deleted")

    def __str__(self):
        return f"{self.account} - {self.amount}"

    @property
    def tax_amount(self):
        if not self.tax or not self.tax.rate:
            return 0
        
        # Get effective tax rate (handle CGST/SGST pair)
        tax_rate = float(self.tax.rate)
        if self.tax.taxtype in ('CGST', 'SGST'):
            from Tax.models import Tax
            counterpart_type = 'SGST' if self.tax.taxtype == 'CGST' else 'CGST'
            counterpart = Tax.objects.filter(taxtype=counterpart_type, rate=self.tax.rate).first()
            if counterpart:
                tax_rate = tax_rate * 2  # Combined rate for CGST+SGST
        
        rate = tax_rate / 100.0
        amount = float(self.amount)

        if self.expense.amount_is == 'exclusive':
            return amount * rate
        else:
            # For inclusive, extract base and calculate tax
            base = amount / (1 + rate)
            return amount - base

    @property 
    def total_amount(self):
        if not self.tax:
            return float(self.amount)
            
        # Get effective tax rate (handle CGST/SGST pair)
        tax_rate = float(self.tax.rate)
        if self.tax.taxtype in ('CGST', 'SGST'):
            from Tax.models import Tax
            counterpart_type = 'SGST' if self.tax.taxtype == 'CGST' else 'CGST'
            counterpart = Tax.objects.filter(taxtype=counterpart_type, rate=self.tax.rate).first()
            if counterpart:
                tax_rate = tax_rate * 2  # Combined rate for CGST+SGST
        
        amount = float(self.amount)
        rate = tax_rate / 100.0

        if self.expense.amount_is == 'exclusive':
            # For exclusive: add tax to base
            return amount * (1 + rate)
        else:
            # For inclusive: amount already includes tax
            return amount