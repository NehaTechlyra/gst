from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from Items.models import Item
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from chart_of_accounts.models import ChartOfAccounts
from django.db.models import Max
from django.db.models import Sum
from warehouse.models import Warehouse
from django.db import transaction
from stock.models import Stock
from customer.models import GstTreatment
from django_countries.fields import CountryField
# Create your models here.
#vendor

class Vendor(models.Model):
    VENDOR_TYPE_CHOICES = [
        
        
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]
    TAX_PREFERENCE_CHOICES = [
        ('taxable', 'Taxable'),
        ('tax_exempt', 'Tax Exempt'),
    ]

    vendor_code = models.CharField(max_length=20, unique=False, default='', help_text="Unique vendor identifier")
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES, default='individual')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    # Billing Address
    address_line_1 = models.CharField(max_length=255, default='')
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, default='')
    state = models.CharField(max_length=100, default='')
    postal_code = models.CharField(max_length=15, default='')
    country = CountryField(blank=True, null=True, verbose_name="Billing Country")
    # Shipping Address
    shipping_address_line_1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=15, blank=True, null=True, verbose_name="Shipping Postal Code")
    shipping_country = CountryField(blank=True, null=True, verbose_name="Shipping Country")
    tax_number = models.CharField(max_length=30, blank=True, null=True, help_text="Tax ID or GST number")
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
        related_name='vendors',
        help_text="Payment terms for this customer"
    )
    opening_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Opening balance for the vendor account"
    )
    #added by neha on 22-1-26
    gst_treatment = models.ForeignKey(
        GstTreatment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='vendors',
        help_text="GST treatment applicable for this customer"
    )
    is_active = models.BooleanField(default=True)
    is_customer = models.BooleanField(default=False, help_text="Check if this vendor is also a customer")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='vendors_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this vendor"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='vendors_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this vendor"
    )

    class Meta:
        ordering = ['vendor_code']
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        if self.vendor_type == 'company':
            return self.company_name or self.vendor_code
        else:
            return f"{self.first_name} {self.last_name or ''}".strip() or self.vendor_code


class ContactPerson(models.Model):
    vendor = models.ForeignKey(Vendor, related_name='contact_persons', on_delete=models.CASCADE)
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})" if self.name or self.email else str(self.id)  

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    contact = models.CharField(max_length=50)
    address = models.TextField()

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
#edited by neha on 17-12-25
class OrderPrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Issued', 'Issued'),
        ('Billed', 'Billed'),
        ('Cancelled', 'Cancelled'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=timezone.now)
    
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')], default='flat')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_bills',
    )
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from bill currency to company base currency.',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    
    # Shi by adarshpping address fields
    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")
    TDS_TCS_TYPE_CHOICES = [
        ('tds', 'TDS'),
        ('tcs', 'TCS'),
    ]
    tds_tcs_type = models.CharField(
        max_length=10,
        choices=TDS_TCS_TYPE_CHOICES,
        default='tds',
        blank=True,
        null=True,
        verbose_name='TDS/TCS Type'
    )
    tds_tcs_definition_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='TDS/TCS Definition ID'
    )
    tds_tcs_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='TDS/TCS Rate'
    )
    tds_tcs_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='TDS/TCS Amount'
    )
   # added by adarsh

    def get_currency_symbol(self):
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code
        if self.vendor and self.vendor.currency:
            # If vendor has a preferred currency code, try to find it
            from currencies.models import Currency
            c = Currency.objects.filter(code=self.vendor.currency).first()
            if c:
                return c.symbol or c.code
        return "₹"

    def __str__(self):
        return f"Order-{self.pk} - {self.vendor.first_name}"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=0, max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=4)
    o_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"






# added by neha on 17-12-25

class PaymentStatus(models.Model):
    STATUS_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]

    
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

#added by neha on 17-1-26
class BillPrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix

class Bill(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Open', 'Open'),
        ('Closed', 'Closed'),
       
    ]
    payment_status = models.ForeignKey(
        PaymentStatus,
        on_delete=models.PROTECT,
        default=1,
        null=True,
        blank=True
    )

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    order_number = models.ForeignKey(PurchaseOrder, related_name='bills',  null=True,on_delete=models.CASCADE)
    bill_number = models.CharField(max_length=20, unique=True)
    order = models.CharField(max_length=20,null=True,blank=True)
    date = models.DateField(default=timezone.now)
    
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')], default='flat')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    warehouse=models.ForeignKey(Warehouse, on_delete=models.CASCADE,null=True)
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_bill_currencies',
    )
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from bill currency to company base currency.',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    
    # Shipping by adarshaddress fields
    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")
    TDS_TCS_TYPE_CHOICES = [
        ('tds', 'TDS'),
        ('tcs', 'TCS'),
    ]
    tds_tcs_type = models.CharField(
        max_length=10,
        choices=TDS_TCS_TYPE_CHOICES,
        default='tds',
        blank=True,
        null=True,
        verbose_name='TDS/TCS Type'
    )
    tds_tcs_definition_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='TDS/TCS Definition ID'
    )
    tds_tcs_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='TDS/TCS Rate'
    )
    tds_tcs_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='TDS/TCS Amount'
    )
    # added by adarsh

    def get_currency_symbol(self):
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code
        if self.vendor and self.vendor.currency:
            try:
                from currencies.models import Currency
                c = Currency.objects.filter(code=self.vendor.currency, is_active=True).first()
                if c:
                    return c.symbol or c.code
            except Exception:
                pass
            return self.vendor.currency
        return "₹"

    def __str__(self):
        return f"{self.bill_number}"

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=0, max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=4)
    o_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    
    # updtd by sree on 27-01-26 for delivery quantity tracking
    def get_previously_delivered(self):
        """Get total quantity already delivered"""
        return DeliveryNoteItem.objects.filter(
            bill_item=self,
            delivery_note__stock_updated=True
        ).aggregate(total=Sum('quantity_delivered'))['total'] or 0
    
    def get_remaining_quantity(self):
        """Get remaining quantity to be delivered"""
        return self.quantity - self.get_previously_delivered()
    
    def get_delivery_percentage(self):
        """Get delivery completion percentage"""
        if self.quantity == 0:
            return 0
        delivered = self.get_previously_delivered()
        print("previously delivery percentage",delivered)
        return int((delivered / self.quantity) * 100)

class PaymentMode(models.Model):
    """Payment modes for transactions"""
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'payment_mode'
        ordering = ['name']
        verbose_name = 'Payment Mode'
        verbose_name_plural = 'Payment Modes'

    def __str__(self):
        return self.name

class BillPayment(models.Model):
    """Records payments made to vendors (can be for multiple bills or advance payment)"""
    
    # Foreign Keys
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.PROTECT,
        related_name='bill_payments',
        help_text='Vendor receiving the payment'
    )
    payment_mode = models.ForeignKey(
        'PaymentMode',
        on_delete=models.PROTECT,
        related_name='bill_payments',
        null=True, blank=True
    )
    paid_through = models.ForeignKey(
        'chart_of_accounts.ChartOfAccounts',
        on_delete=models.PROTECT,
        related_name='bill_payments',
        help_text='Account from which payment was made'
    )
    
    # Payment Details
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Total payment amount'
    )
    payment_number = models.PositiveIntegerField(unique=True)
    payment_date = models.DateField(
        help_text='Date of payment transaction'
    )
    payment_made_on = models.DateField(
        null=True,
        blank=True,
        help_text='Actual date when payment was made (if different)'
    )
    
    # Additional Information
    reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='External reference number (check number, transaction ID, etc.)'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes about the payment'
    )
    
    # Email Notification
    send_email = models.BooleanField(
        default=False,
        help_text='Send payment notification email'
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bill_payments'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_bill_payments'
    )
    
    class Meta:
        db_table = 'bill_payment'
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Bill Payment'
        verbose_name_plural = 'Bill Payments'
        indexes = [
            models.Index(fields=['vendor', 'payment_date']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['payment_date']),
        ]

    def get_currency_symbol(self):
        first_allocation = self.bill_allocations.select_related('bill__document_currency').first()
        if first_allocation and first_allocation.bill:
            return first_allocation.bill.get_currency_symbol()
        if self.vendor and self.vendor.currency:
            try:
                from currencies.models import Currency
                c = Currency.objects.filter(code=self.vendor.currency, is_active=True).first()
                if c:
                    return c.symbol or c.code
            except Exception:
                pass
            return self.vendor.currency
        return "₹"

    def __str__(self):
        bill_count = self.bill_allocations.count()
        sym = self.get_currency_symbol()
        if bill_count > 0:
            if bill_count == 1:
                bill = self.bill_allocations.first().bill
                return f"Payment #{self.payment_number} - Bill #{bill.bill_number} - {sym}{self.amount}"
            else:
                return f"Payment #{self.payment_number} - {bill_count} Bills - {sym}{self.amount}"
        return f"Advance Payment #{self.payment_number} - {self.vendor} - {sym}{self.amount}"
    
    def save(self, *args, **kwargs):
        # Auto-generate payment number if not provided
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_payment_number():
        last_number = BillPayment.objects.aggregate(
            max_no=Max('payment_number')
        )['max_no']

        return (last_number or 0) + 1
    
    @property
    def is_advance_payment(self):
        """Check if this is an advance payment (no bills associated)"""
        return self.bill_allocations.count() == 0
    
    @property
    def allocated_amount(self):
        """Total amount allocated to bills"""
        return self.bill_allocations.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def advance_amount(self):
        """Amount not allocated to any bill (advance payment)"""
        return self.amount - self.allocated_amount


class BillPaymentAllocation(models.Model):
    """Links payments to bills with specific allocation amounts"""
    
    payment = models.ForeignKey(
        BillPayment,
        on_delete=models.CASCADE,
        related_name='bill_allocations'
    )
    bill = models.ForeignKey(
        'Bill',
        on_delete=models.CASCADE,
        related_name='payment_allocations'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Amount allocated to this bill from the payment'
    )
    payment_made_on = models.DateField(
        null=True,
        blank=True,
        help_text='Specific payment date for this bill (if different from main payment)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bill_payment_allocation'
        ordering = ['bill__bill_number']
        verbose_name = 'Bill Payment Allocation'
        verbose_name_plural = 'Bill Payment Allocations'
        unique_together = [['payment', 'bill']]
        indexes = [
            models.Index(fields=['payment', 'bill']),
            models.Index(fields=['bill']),
        ]
    
    def __str__(self):
        return f"Payment #{self.payment.payment_number} → Bill #{self.bill.bill_number}: ₹{self.amount}"


class BillPaymentAttachment(models.Model):
    """Attachments for bill payments"""
    
    payment = models.ForeignKey(
        BillPayment,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='bill_payments/%Y/%m/',
        help_text='Payment related document'
    )
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text='File size in bytes')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = 'bill_payment_attachment'
        ordering = ['-uploaded_at']
        verbose_name = 'Payment Attachment'
        verbose_name_plural = 'Payment Attachments'
    
    def __str__(self):
        return f"{self.file_name} - Payment #{self.payment.payment_number}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)

class VendorAdvancePayment(models.Model):
    """
    Simplified table to track vendor advance balance with payment reference.
    - Positive amount = Credit (advance payment made to vendor)
    - Negative amount = Debit (advance used for bill payment)
    - Balance = Sum of all amounts for a vendor
    """
    
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.PROTECT,
        related_name='advance_payments',
        help_text='Vendor for whom advance is maintained'
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Amount: positive for credit (advance given), negative for debit (advance used)'
    )
    
    payment = models.ForeignKey(
        'BillPayment',
        on_delete=models.PROTECT,
        related_name='advance_transactions',
        null=True,
        blank=True,
        help_text='Reference to the payment that created or used this advance'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vendor_advance_payment'
        ordering = ['-created_at']
        verbose_name = 'Vendor Advance Payment'
        verbose_name_plural = 'Vendor Advance Payments'
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['payment']),
        ]
    
    def __str__(self):
        transaction_type = "Credit" if self.amount > 0 else "Debit"
        payment_ref = f" (Payment #{self.payment.payment_number})" if self.payment else ""
        return f"{self.vendor} - {transaction_type} ₹{abs(self.amount)}{payment_ref}"
    
    @staticmethod
    def get_vendor_advance_balance(vendor_id):
        """
        Calculate current advance balance for a vendor.
        Sum of all amounts (positive credits + negative debits = net balance)
        
        Args:
            vendor_id: ID of the vendor
            
        Returns:
            Decimal: Current advance balance
            
        Example:
            vendor_id=5 has transactions:
            +5000 (Payment #101), -2000 (Payment #105), +3000 (Payment #110), -1500 (Payment #112)
            Balance = 5000 - 2000 + 3000 - 1500 = 4500
        """
        try:
            from Purchase.models import Vendor
            vendor = Vendor.objects.get(pk=vendor_id)
        except Vendor.DoesNotExist:
            return Decimal('0.00')
        
        # Sum all amounts (positive and negative)
        balance = VendorAdvancePayment.objects.filter(
            vendor=vendor
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return balance
    
    @staticmethod
    def add_advance(vendor, amount, payment=None):
        """
        Add advance payment (credit) for a vendor.
        Creates a positive entry in the table.
        
        Args:
            vendor: Vendor object
            amount: Decimal amount to add (will be stored as positive)
            payment: BillPayment object (optional, to track source)
            
        Returns:
            VendorAdvancePayment object
            
        Example:
            VendorAdvancePayment.add_advance(vendor, Decimal('5000.00'), payment_obj)
            → Creates entry with amount = +5000.00 and payment reference
        """
        advance = VendorAdvancePayment.objects.create(
            vendor=vendor,
            amount=abs(amount),  # Ensure positive
            payment=payment
        )
        return advance
    
    @staticmethod
    def use_advance(vendor, amount, payment=None):
        """
        Use advance payment (debit) for bill payment.
        Creates a negative entry in the table.
        
        Args:
            vendor: Vendor object
            amount: Decimal amount to use (will be stored as negative)
            payment: BillPayment object (optional, to track usage)
            
        Returns:
            VendorAdvancePayment object if successful
            None if insufficient balance
            
        Example:
            Current balance: 5000
            VendorAdvancePayment.use_advance(vendor, Decimal('2000.00'), payment_obj)
            → Creates entry with amount = -2000.00 and payment reference
            → New balance: 3000
        """
        # Check if sufficient balance
        current_balance = VendorAdvancePayment.get_vendor_advance_balance(vendor.id)
        
        if current_balance < amount:
            return None  # Insufficient advance balance
        
        # Create debit entry (negative amount)
        advance = VendorAdvancePayment.objects.create(
            vendor=vendor,
            amount=-abs(amount),  # Ensure negative
            payment=payment
        )
        return advance
    
    @staticmethod
    def get_advance_history(vendor_id, limit=None):
        """
        Get advance transaction history for a vendor.
        
        Args:
            vendor_id: ID of the vendor
            limit: Optional limit on number of records
            
        Returns:
            QuerySet of VendorAdvancePayment objects
            
        Example:
            history = VendorAdvancePayment.get_advance_history(vendor_id=5, limit=10)
            for txn in history:
                print(f"{txn.created_at}: ₹{txn.amount} - Payment #{txn.payment.payment_number}")
        """
        query = VendorAdvancePayment.objects.filter(
            vendor_id=vendor_id
        ).select_related('payment', 'vendor').order_by('-created_at')
        
        if limit:
            query = query[:limit]
        
        return query
    

# delivery details model by sreevidya




class DeliveryNote(models.Model):
    STATUS_CHOICES = [
        # ('pending', 'Pending'),
        # ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    bill = models.ForeignKey('Bill', related_name='delivery_notes', on_delete=models.CASCADE)
    delivery_note_number = models.CharField(max_length=20, unique=True)
    delivery_date = models.DateField(default=timezone.now)
    received_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Warehouse from which items are being shipped
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Track if stock has been updated
    stock_updated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-delivery_date']

    def __str__(self):
        return f"DN-{self.delivery_note_number} for Bill-{self.bill.bill_number}"
    
    def save(self, *args, **kwargs):
        if not self.delivery_note_number:
            # Auto-generate delivery note number
            last_dn = DeliveryNote.objects.order_by('-id').first()
            if last_dn and last_dn.delivery_note_number:
                try:
                    last_number = int(last_dn.delivery_note_number.split('-')[-1])
                    self.delivery_note_number = f"DN-{last_number + 1:05d}"
                except (ValueError, IndexError):
                    self.delivery_note_number = "DN-00001"
            else:
                self.delivery_note_number = "DN-00001"
        super().save(*args, **kwargs)
    
    def update_stock(self, user=None):
        """
        Update stock when delivery is marked as delivered
        """
        if self.status == 'delivered' and not self.stock_updated:
            with transaction.atomic():
                db = self._state.db or 'default'
                warehouse = Warehouse.objects.using(db).filter(pk=self.warehouse_id).first() or self.warehouse
                
                for delivery_item in DeliveryNoteItem.objects.using(db).filter(
                    delivery_note_id=self.id
                ).select_related('bill_item__product'):
                    product = delivery_item.bill_item.product

                    if not getattr(product, 'track_inventory', False):
                        continue
                    
                    # Get or create stock entry for this product in this warehouse
                    stock, created = Stock.objects.using(db).get_or_create(
                        item=product,
                        warehouse=warehouse,
                        batch_number=None,
                        serial_number=None,
                        defaults={
                            'quantity': Decimal('0.00'),
                            'status': True
                        }
                    )
                    
                    # Increase stock quantity
                    old_quantity = stock.quantity
                    stock.quantity += delivery_item.quantity_delivered
                    stock.save(using=db)
                    
                    print(f"Stock updated for {product.name}: {old_quantity} -> {stock.quantity}")
                    
                    # Create stock movement record
                    StockMovement.objects.using(db).create(
                        stock=stock,
                        movement_type='in',
                        quantity=delivery_item.quantity_delivered,
                        reference_type='delivery_note',
                        reference_id=self.id,
                        delivery_note=self,
                        notes=f"Stock in from Delivery Note {self.delivery_note_number}",
                        created_by=user,
                    )
                
                # Mark stock as updated
                self.stock_updated = True
                self.save(using=db, update_fields=['stock_updated'])
                print(f"Delivery Note {self.delivery_note_number} - Stock updated successfully")
    
    def reverse_stock(self, user=None):
        """
        Reverse stock update if delivery is cancelled
        """
        if self.stock_updated and self.status == 'cancelled':
            with transaction.atomic():
                db = self._state.db or 'default'
                warehouse = Warehouse.objects.using(db).filter(pk=self.warehouse_id).first() or self.warehouse
                
                for delivery_item in DeliveryNoteItem.objects.using(db).filter(
                    delivery_note_id=self.id
                ).select_related('bill_item__product'):
                    product = delivery_item.bill_item.product

                    if not getattr(product, 'track_inventory', False):
                        continue
                    
                    try:
                        stock = Stock.objects.using(db).get(
                            item=product,
                            warehouse=warehouse,
                            batch_number=None,
                            serial_number=None
                        )
                        
                        # Decrease stock quantity
                        if stock.quantity >= delivery_item.quantity_delivered:
                            stock.quantity -= delivery_item.quantity_delivered
                            stock.save(using=db)
                            
                            # Create stock movement record for reversal
                            StockMovement.objects.using(db).create(
                                stock=stock,
                                movement_type='out',
                                quantity=delivery_item.quantity_delivered,
                                reference_type='delivery_note_reversal',
                                reference_id=self.id,
                                delivery_note=self,
                                notes=f"Stock reversal for cancelled Delivery Note {self.delivery_note_number}",
                                created_by=user,
                            )
                        else:
                            raise ValidationError(
                                f"Insufficient stock to reverse. Available: {stock.quantity}, "
                                f"Required: {delivery_item.quantity_delivered}"
                            )
                    except Stock.DoesNotExist:
                        raise ValidationError(
                            f"Stock entry not found for {product.name}"
                        )
                
                # Mark stock as not updated
                self.stock_updated = False
                self.save(using=db, update_fields=['stock_updated'])


class DeliveryNoteItem(models.Model):
    delivery_note = models.ForeignKey(DeliveryNote, related_name='items', on_delete=models.CASCADE)
    bill_item = models.ForeignKey('BillItem', on_delete=models.CASCADE)
    quantity_delivered = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['delivery_note', 'bill_item']
    
    def __str__(self):
        return f"{self.bill_item.product.name} - {self.quantity_delivered}"
    
    def clean(self):
        # Check if quantity delivered exceeds ordered quantity
        total_delivered = DeliveryNoteItem.objects.filter(
            bill_item=self.bill_item,
            delivery_note__stock_updated=True
        ).exclude(pk=self.pk).aggregate(
            total=Sum('quantity_delivered')
        )['total'] or 0
        
        if (total_delivered + self.quantity_delivered) > self.bill_item.quantity:
            raise ValidationError(
                f"Total delivered quantity ({total_delivered + self.quantity_delivered}) "
                f"exceeds ordered quantity ({self.bill_item.quantity})"
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """
    Track all stock movements for audit trail
    """
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
    ]
    
    REFERENCE_TYPE_CHOICES = [
        ('delivery_note', 'Delivery Note'),
        ('delivery_note_reversal', 'Delivery Note Reversal'),
        ('purchase_bill_payment', 'Purchase Bill Payment'),
        ('purchase_return', 'Purchase Return'),
        ('sales_order', 'Sales Order'),
        ('adjustment', 'Manual Adjustment'),
        ('transfer', 'Warehouse Transfer'),
    ]
    
    stock = models.ForeignKey('stock.Stock', related_name='movements', on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reference to source document
    reference_type = models.CharField(max_length=50, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.PositiveIntegerField()
    delivery_note = models.ForeignKey(
        DeliveryNote, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='stock_movements'
    )
    purchase_return = models.ForeignKey(
        'PurchaseReturn',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
    
    def __str__(self):
        return f"{self.movement_type} - {self.stock.item.name} - {self.quantity}"


class PurchaseReturn(models.Model):
    """Represents a purchase return / debit note for a Bill."""
    bill = models.ForeignKey(Bill, related_name='returns', on_delete=models.CASCADE)
    return_number = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField(default=timezone.now)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    received_by = models.CharField(max_length=255, blank=True, null=True)
    shipped_by = models.CharField(max_length=255, blank=True, null=True)
    courier_name = models.CharField(max_length=255, blank=True, null=True)
    tracking_number = models.CharField(max_length=255, blank=True, null=True)
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_returns',
    )
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from purchase return currency to company base currency.',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    stock_updated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PR-{self.return_number} for {self.bill.bill_number}"

    def save(self, *args, **kwargs):
        if not self.return_number:
            last = PurchaseReturn.objects.order_by('-id').first()
            if last and last.return_number:
                try:
                    last_no = int(last.return_number.split('-')[-1])
                    self.return_number = f"PR-{last_no + 1:05d}"
                except Exception:
                    self.return_number = "PR-00001"
            else:
                self.return_number = "PR-00001"
        super().save(*args, **kwargs)

    def get_currency_symbol(self):
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code
        if self.bill_id and getattr(self.bill, 'document_currency', None):
            return self.bill.document_currency.symbol or self.bill.document_currency.code
        if self.vendor and self.vendor.currency:
            try:
                from currencies.models import Currency
                c = Currency.objects.filter(code=self.vendor.currency, is_active=True).first()
                if c:
                    return c.symbol or c.code
            except Exception:
                pass
            return self.vendor.currency
        return "₹"


class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, related_name='items', on_delete=models.CASCADE)
    bill_item = models.ForeignKey(BillItem, on_delete=models.CASCADE)
    quantity_returned = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Return {self.purchase_return.return_number} - {self.bill_item.product.name}: {self.quantity_returned}"
