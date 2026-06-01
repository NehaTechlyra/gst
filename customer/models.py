from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django_countries.fields import CountryField
#added by neha on 22-1-26
class GstTreatment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'gst_treatment'
        verbose_name_plural = "Gst Treatment"

    def __str__(self):
        return self.name
class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]
    TAX_PREFERENCE_CHOICES = [
        ('taxable', 'Taxable'),
        ('tax_exempt', 'Tax Exempt'),
    ]

    customer_code = models.CharField(max_length=20, unique=True, help_text="Unique customer identifier")
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    is_draft = models.BooleanField(default=False)  # ← Add this line
    # Billing Address
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=15)
    country = CountryField(verbose_name="Billing Country")
    # Shipping Address
    shipping_address_line_1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=15, blank=True, null=True, verbose_name="Shipping Postal Code")
    shipping_country = CountryField(blank=True, null=True, verbose_name="Shipping Country")

    gst_number = models.CharField(max_length=30, blank=True, null=True, help_text="Tax ID or GST number")
    pan_number = models.CharField(max_length=10, blank=True, null=True, help_text="PAN (Permanent Account Number)")
    tax_preference = models.CharField(
        max_length=20, 
        choices=TAX_PREFERENCE_CHOICES, 
        default='taxable',
        help_text="Tax preference for this customer",blank=True, null=True,
    )
    exemption_reason = models.TextField(blank=True, null=True, help_text="Reason for tax exemption (if applicable)")
    # Financial fields
    currency = models.CharField(max_length=10, default='INR', help_text="Currency code (e.g., INR, USD)",blank=True, null=True,)
    payment_terms = models.ForeignKey(
        'PayTerms.PayTerms',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='customers',
        help_text="Payment terms for this customer"
    )
    opening_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Opening balance for the customer account"
    )
    #added by neha on 22-1-26
    gst_treatment = models.ForeignKey(
        GstTreatment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='customers',
        help_text="GST treatment applicable for this customer"
    )
    is_active = models.BooleanField(default=True)
    is_vendor = models.BooleanField(default=False, help_text="Check if this customer is also a vendor")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='customers_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this customer"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='customers_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this customer"
    )

    class Meta:
        ordering = ['customer_code']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        if self.customer_type == 'company':
            return self.company_name or self.customer_code
        else:
            return f"{self.first_name} {self.last_name or ''}".strip() or self.customer_code

    def get_currency_symbol(self):
        """Returns the appropriate currency symbol for this customer."""
        if self.currency:
            try:
                from currencies.models import Currency
                cur = Currency.objects.filter(code__iexact=self.currency).first()
                if cur:
                    return cur.symbol or cur.code or '₹'
                return self.currency
            except Exception:
                return '₹'
        return '₹'


class ContactPerson(models.Model):
    customer = models.ForeignKey(Customer, related_name='contact_persons', on_delete=models.CASCADE)
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})" if self.name or self.email else str(self.id)

