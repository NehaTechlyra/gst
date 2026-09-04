from django.db import models
from customer.models import Customer
from Items.models import Item
from django.utils import timezone
from Tax.models import Tax, TaxGroup
from Purchase.models import PaymentMode,PaymentStatus
from django.contrib.auth.models import User
from django.db.models import Max
from django.db.models import Sum
from decimal import Decimal
from warehouse.models import Warehouse
from django.db import transaction
from stock.models import Stock
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string



class SalesPerson(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name")
    email = models.EmailField(max_length=254, unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone Number")
    def __str__(self):
        return self.name

class QuotePrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix

# Create your models here.
class SalesQuotation(models.Model):
    # STATUS_CHOICES = [
    #     ('DRAFT', 'Draft'),
    #     ('PENDING', 'Pending Approval'),
    #     ('APPROVED', 'Approved'),
    #     ('SENT', 'Sent to Supplier'),
    # ]
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Invoiced', 'Invoiced'),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('flat', 'Flat Amount'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    quote_number = models.CharField(max_length=20, unique=True, verbose_name="Quote#")
    # date = models.DateField(auto_now_add=True)
    date = models.DateField(default=timezone.now)
    sales_person = models.ForeignKey(SalesPerson, on_delete=models.CASCADE, null=True, blank=True)
    # Link to payment terms (optional)
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)

    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name="Discount Value")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='flat', verbose_name="Discount Type")
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")
    
    # Shipping address fields
    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    
    # Currency fields (matching SalesInvoice)
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from quotation currency to company base currency.',
    )
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_quotations',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    turnover_tax = models.ForeignKey(
        'Tax.Tax',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_quotations_turnover_tax',
    )
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

    def __str__(self):
        return f'{self.quote_number} - {self.customer.first_name if self.customer else "N/A"}'

    def get_currency_symbol(self):
        """Returns the appropriate currency symbol for this quotation."""
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code or '₹'
        
        # Fallback to customer's default currency if document currency is not set
        if self.customer and hasattr(self.customer, 'currency') and self.customer.currency:
            try:
                from currencies.models import Currency
                customer_cur = Currency.objects.filter(code__iexact=self.customer.currency).first()
                if customer_cur:
                    return customer_cur.symbol or customer_cur.code or '₹'
                return self.customer.currency
            except Exception:
                return '₹'
        
        return '₹'  # Default fallback

# class PurchaseOrderItem(models.Model):
#     po = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     price = models.DecimalField(max_digits=10, decimal_places=2)

#     def line_total(self):
#         return self.quantity * self.price

class SalesQuotationItem(models.Model):
    Sales_quotation = models.ForeignKey(SalesQuotation, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)  # link to Item model
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)  # new field
    # prd_tax = models.CharField(max_length=100, blank=True, null=True)  # new field
    # prd_tax = models.ForeignKey('Tax.TaxGroup', on_delete=models.SET_NULL, null=True, blank=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=Decimal('0.00'), max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    # prd_tax = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6)
    o_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0.000000'))  # Base currency price
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class OrderPrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix

class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Invoiced', 'Invoiced'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=timezone.now)
    sales_person = models.ForeignKey(SalesPerson, on_delete=models.CASCADE, null=True, blank=True)
    # Link to payment terms (optional)
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')], default='flat')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from order currency to company base currency.',
    )
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    turnover_tax = models.ForeignKey(
        'Tax.Tax',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders_turnover_tax',
    )
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")
    
    # Shipping address fields
    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")
    origin_performa = models.ForeignKey('sales.PerformaInvoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
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

    def __str__(self):
        return f"Order-{self.pk} - {self.customer.first_name}"

    def get_currency_symbol(self):
        """Returns the appropriate currency symbol for this order."""
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code or '₹'
        
        # Fallback to customer's default currency if document currency is not set
        if self.customer and hasattr(self.customer, 'currency') and self.customer.currency:
            try:
                from currencies.models import Currency
                # We try to find a currency matching the customer's currency code
                # Note: this might need adjustment if multiple companies have different symbols for same code,
                # but typically symbols are consistent per currency code.
                customer_cur = Currency.objects.filter(code__iexact=self.customer.currency).first()
                if customer_cur:
                    return customer_cur.symbol or customer_cur.code or '₹'
                return self.customer.currency
            except Exception:
                return '₹'
        
        return '₹'

class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=Decimal('0.00'), max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6)
    o_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0.000000'))  # Base currency price
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class InvoicePrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix


class SalesInvoice(models.Model):
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
        blank=True,
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    inv_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=timezone.now)
    sales_person = models.ForeignKey(SalesPerson, on_delete=models.CASCADE, null=True, blank=True)
    # Link to payment terms (optional)
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')], default='flat')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from invoice currency to company base currency.',
    )
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_invoices',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")
    
    # Shipping address fields
    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")

    # Link back to originating quotation (if created from a quotation)
    origin_quote = models.ForeignKey(SalesQuotation, on_delete=models.SET_NULL, null=True, blank=True)
    turnover_tax = models.ForeignKey(
        Tax,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_invoices_turnover_tax',
    )
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
    def __str__(self):
        # return f"Order-{self.pk} - {self.customer.first_name}"//commented by sree on 11-o2-2026
        return f"{self.inv_number}"
    
    def get_currency_symbol(self):
        """Returns the appropriate currency symbol for this invoice."""
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code or '₹'
        
        # Fallback to customer's default currency if document currency is not set
        if self.customer and hasattr(self.customer, 'currency') and self.customer.currency:
            try:
                from currencies.models import Currency
                customer_cur = Currency.objects.filter(code__iexact=self.customer.currency).first()
                if customer_cur:
                    return customer_cur.symbol or customer_cur.code or '₹'
                return self.customer.currency
            except Exception:
                return '₹'
        
        return '₹'
    
    def delete(self, *args, **kwargs):
        """Delete the invoice and its associated journal entries"""
        from journal.models import JournalEntry
        
        # Delete journal entries that reference this invoice
        JournalEntry.objects.filter(reference=self.inv_number).delete()
        
        # Call the parent delete method
        super().delete(*args, **kwargs)


class InvoiceTax(models.Model):
    invoice = models.ForeignKey(SalesInvoice, related_name='taxes', on_delete=models.CASCADE)
    tax_name = models.CharField(max_length=255)
    tax_rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['invoice_id', 'id']
        verbose_name = "Invoice Tax"
        verbose_name_plural = "Invoice Taxes"

    def __str__(self):
        return f"{self.invoice.inv_number} - {self.tax_name} {self.tax_rate}%"

class SalesInvoiceItem(models.Model):
    sales_inv = models.ForeignKey(SalesInvoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=Decimal('0.00'), max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6)
    o_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0.000000'))  # Base currency price
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    
    # updtd by sree on 04-03-26 for delivery quantity tracking
    def get_previously_delivered(self):
        """Get total quantity already delivered"""
        return SalesDeliveryNoteItem.objects.filter(
            invoice_item=self,
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


class InvPayment(models.Model):
    """Records payments made to customers (can be for multiple Invs or advance payment)"""
    
    # Foreign Keys
    customer = models.ForeignKey(
        'customer.Customer',
        on_delete=models.PROTECT,
        related_name='inv_payments',
        help_text='Customer receiving the payment'
    )
    payment_mode = models.ForeignKey(
        'Purchase.PaymentMode',
        on_delete=models.PROTECT,
        related_name='inv_payments',
        null=True,
        blank=True,
    )
    paid_through = models.ForeignKey(
        'chart_of_accounts.ChartOfAccounts',
        on_delete=models.PROTECT,
        related_name='inv_payments',
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
        related_name='created_inv_payments'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_inv_payments'
    )
    
    class Meta:
        db_table = 'inv_payment'
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Inv Payment'
        verbose_name_plural = 'Inv Payments'
        indexes = [
            models.Index(fields=['customer', 'payment_date']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['payment_date']),
        ]
    
    def get_currency_symbol(self):
        if self.customer:
            return self.customer.get_currency_symbol()
        return '₹'
        
    def __str__(self):
        sym = self.get_currency_symbol()
        inv_count = self.inv_allocations.count()
        if inv_count > 0:
            if inv_count == 1:
                inv = self.inv_allocations.first().inv
                return f"Payment #{self.payment_number} - Inv #{inv.inv_number} - {sym}{self.amount}"
            else:
                return f"Payment #{self.payment_number} - {inv_count} Invs - {sym}{self.amount}"
        return f"Advance Payment #{self.payment_number} - {self.customer} - {sym}{self.amount}"
    
    def save(self, *args, **kwargs):
        # Auto-generate payment number if not provided
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_payment_number():
        last_number = InvPayment.objects.aggregate(
            max_no=Max('payment_number')
        )['max_no']

        return (last_number or 0) + 1
    
    @property
    def is_advance_payment(self):
        """Check if this is an advance payment (no invs associated)"""
        return self.inv_allocations.count() == 0
    
    @property
    def allocated_amount(self):
        """Total amount allocated to invs"""
        return self.inv_allocations.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def advance_amount(self):
        """Amount not allocated to any inv (advance payment)"""
        return self.amount - self.allocated_amount


class InvPaymentAllocation(models.Model):
    """Links payments to invs with specific allocation amounts"""
    
    payment = models.ForeignKey(
        InvPayment,
        on_delete=models.CASCADE,
        related_name='inv_allocations'
    )
    inv = models.ForeignKey(
        'SalesInvoice',
        on_delete=models.CASCADE,
        related_name='payment_allocations'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Amount allocated to this inv from the payment'
    )
    payment_made_on = models.DateField(
        null=True,
        blank=True,
        help_text='Specific payment date for this inv (if different from main payment)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inv_payment_allocation'
        ordering = ['inv__inv_number']
        verbose_name = 'Inv Payment Allocation'
        verbose_name_plural = 'Inv Payment Allocations'
        unique_together = [['payment', 'inv']]
        indexes = [
            models.Index(fields=['payment', 'inv']),
            models.Index(fields=['inv']),
        ]
    
    def __str__(self):
        return f"Payment #{self.payment.payment_number} → Inv #{self.inv.inv_number}: ₹{self.amount}"


class InvPaymentAttachment(models.Model):
    """Attachments for inv payments"""
    
    payment = models.ForeignKey(
        InvPayment,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='inv_payments/%Y/%m/',
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
        db_table = 'inv_payment_attachment'
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


class CustomerAdvancePayment(models.Model):
    """
    Simplified table to track customer advance balance with payment reference.
    - Positive amount = Credit (advance payment received from customer)
    - Negative amount = Debit (advance used for invoice payment)
    - Balance = Sum of all amounts for a customer
    """
    
    customer = models.ForeignKey(
        'customer.Customer',
        on_delete=models.PROTECT,
        related_name='advance_payments',
        help_text='Customer for whom advance is maintained'
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Amount: positive for credit (advance received), negative for debit (advance used)'
    )
    
    payment = models.ForeignKey(
        'InvPayment',
        on_delete=models.PROTECT,
        related_name='advance_transactions',
        null=True,
        blank=True,
        help_text='Reference to the payment that created or used this advance'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customer_advance_payment'
        ordering = ['-created_at']
        verbose_name = 'Customer Advance Payment'
        verbose_name_plural = 'Customer Advance Payments'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['payment']),
        ]
    
    def __str__(self):
        transaction_type = "Credit" if self.amount > 0 else "Debit"
        payment_ref = f" (Payment #{self.payment.payment_number})" if self.payment else ""
        return f"{self.customer} - {transaction_type} ₹{abs(self.amount)}{payment_ref}"
    
    @staticmethod
    def get_customer_advance_balance(customer_id):
        """
        Calculate current advance balance for a customer.
        Sum of all amounts (positive credits + negative debits = net balance)
        """
        try:
            from customer.models import Customer
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Decimal('0.00')
        
        balance = CustomerAdvancePayment.objects.filter(
            customer=customer
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return balance
    
    @staticmethod
    def add_advance(customer, amount, payment=None):
        """
        Add advance payment (credit) for a customer.
        Creates a positive entry in the table.
        """
        advance = CustomerAdvancePayment.objects.create(
            customer=customer,
            amount=abs(amount),
            payment=payment
        )
        return advance
    
    @staticmethod
    def use_advance(customer, amount, payment=None):
        """
        Use advance payment (debit) for invoice payment.
        Creates a negative entry in the table.
        Returns None if insufficient balance.
        """
        current_balance = CustomerAdvancePayment.get_customer_advance_balance(customer.id)
        
        if current_balance < amount:
            return None
        
        advance = CustomerAdvancePayment.objects.create(
            customer=customer,
            amount=-abs(amount),
            payment=payment
        )
        return advance
    
    @staticmethod
    def get_advance_history(customer_id, limit=None):
        """Get advance transaction history for a customer."""
        query = CustomerAdvancePayment.objects.filter(
            customer_id=customer_id
        ).select_related('payment', 'customer').order_by('-created_at')
        
        if limit:
            query = query[:limit]
        
        return query
    

class SalesDeliveryNote(models.Model):
    STATUS_CHOICES = [
        # ('pending', 'Pending'),
        # ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        # ('cancelled', 'Cancelled'),
    ]
    
    sales_invoice = models.ForeignKey(SalesInvoice, related_name='delivery_notes', on_delete=models.CASCADE)
    delivery_note_number = models.CharField(max_length=20, unique=True)
    delivery_date = models.DateField(default=timezone.now)
    shipped_by = models.CharField(max_length=100, blank=True, null=True, help_text="Name of person who shipped")
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
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
        verbose_name = "Sales Delivery Note"
        verbose_name_plural = "Sales Delivery Notes"

    def __str__(self):
        return f"SDN-{self.delivery_note_number} for Invoice-{self.sales_invoice.inv_number}"
    
    def save(self, *args, **kwargs):
        if not self.delivery_note_number:
            # Auto-generate delivery note number
            last_dn = SalesDeliveryNote.objects.order_by('-id').first()
            if last_dn and last_dn.delivery_note_number:
                try:
                    last_number = int(last_dn.delivery_note_number.split('-')[-1])
                    self.delivery_note_number = f"SDN-{last_number + 1:05d}"
                except (ValueError, IndexError):
                    self.delivery_note_number = "SDN-00001"
            else:
                self.delivery_note_number = "SDN-00001"
        super().save(*args, **kwargs)
    
    def update_stock(self):
        """
        Update stock when delivery is marked as delivered (REDUCE stock for sales)
        """
        if self.status == 'delivered' and not self.stock_updated:
            with transaction.atomic():
                warehouse = self.warehouse
                
                for delivery_item in self.items.all():
                    product = delivery_item.invoice_item.product

                    if not getattr(product, 'track_inventory', False):
                        # Skip stock adjustments for non-inventory items
                        continue

                    # Get or create the stock entry for this product in this warehouse
                    stock, created = Stock.objects.get_or_create(
                        item=product,
                        warehouse=warehouse,
                        batch_number=None,
                        serial_number=None,
                        defaults={'quantity': Decimal('0.00')}
                    )

                    if stock.quantity < delivery_item.quantity_delivered:
                        print(
                            f"WARNING: Stock for {product.name} going negative. "
                            f"Available: {stock.quantity}, Required: {delivery_item.quantity_delivered}"
                        )

                    # Decrease stock quantity (SALES = STOCK OUT)
                    old_quantity = stock.quantity
                    stock.quantity -= delivery_item.quantity_delivered
                    stock.save()

                    print(f"Stock reduced for {product.name}: {old_quantity} -> {stock.quantity}")

                    # Create stock movement record
                    SalesStockMovement.objects.create(
                        stock=stock,
                        movement_type='out',
                        quantity=delivery_item.quantity_delivered,
                        reference_type='sales_delivery_note',
                        reference_id=self.id,
                        delivery_note=self,
                        notes=f"Stock out from Sales Delivery Note {self.delivery_note_number}"
                    )

                # Mark stock as updated
                self.stock_updated = True
                self.save(update_fields=['stock_updated'])
                print(f"Sales Delivery Note {self.delivery_note_number} - Stock updated successfully")
    
    def reverse_stock(self):
        """
        Reverse stock update if delivery is cancelled (ADD stock back)
        """
        if self.stock_updated and self.status == 'cancelled':
            with transaction.atomic():
                warehouse = self.warehouse
                
                for delivery_item in self.items.all():
                    product = delivery_item.invoice_item.product

                    if not getattr(product, 'track_inventory', False):
                        continue
                    
                    try:
                        stock = Stock.objects.get(
                            item=product,
                            warehouse=warehouse,
                            batch_number=None,
                            serial_number=None
                        )
                        
                        # Increase stock quantity (reversal = add back)
                        stock.quantity += delivery_item.quantity_delivered
                        stock.save()
                        
                        # Create stock movement record for reversal
                        SalesStockMovement.objects.create(
                            stock=stock,
                            movement_type='in',
                            quantity=delivery_item.quantity_delivered,
                            reference_type='sales_delivery_note_reversal',
                            reference_id=self.id,
                            delivery_note=self,
                            notes=f"Stock reversal for cancelled Sales Delivery Note {self.delivery_note_number}"
                        )
                        
                    except Stock.DoesNotExist:
                        raise ValidationError(
                            f"Stock entry not found for {product.name}"
                        )
                
                # Mark stock as not updated
                self.stock_updated = False
                self.save(update_fields=['stock_updated'])


class SalesDeliveryNoteItem(models.Model):
    delivery_note = models.ForeignKey(SalesDeliveryNote, related_name='items', on_delete=models.CASCADE)
    invoice_item = models.ForeignKey(SalesInvoiceItem, on_delete=models.CASCADE)
    quantity_delivered = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['delivery_note', 'invoice_item']
    
    def __str__(self):
        return f"{self.invoice_item.product.name} - {self.quantity_delivered}"
    
    def clean(self):
        # Check if quantity delivered exceeds ordered quantity
        total_delivered = SalesDeliveryNoteItem.objects.filter(
            invoice_item=self.invoice_item,
            delivery_note__stock_updated=True
        ).exclude(pk=self.pk).aggregate(
            total=Sum('quantity_delivered')
        )['total'] or 0
        
        if (total_delivered + self.quantity_delivered) > self.invoice_item.quantity:
            raise ValidationError(
                f"Total delivered quantity ({total_delivered + self.quantity_delivered}) "
                f"exceeds ordered quantity ({self.invoice_item.quantity})"
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class SalesStockMovement(models.Model):
    """
    Track all stock movements for sales deliveries
    """
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
    ]
    
    REFERENCE_TYPE_CHOICES = [
        ('sales_delivery_note', 'Sales Delivery Note'),
        ('sales_delivery_note_reversal', 'Sales Delivery Note Reversal'),
        ('sales_return', 'Sales Return'),
        ('sales_return_reversal', 'Sales Return Reversal'),
        ('sales_invoice_payment', 'Sales Invoice Payment'),
    ]
    
    stock = models.ForeignKey('stock.Stock', related_name='sales_movements', on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reference to source document
    reference_type = models.CharField(max_length=50, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.PositiveIntegerField()
    delivery_note = models.ForeignKey(
        SalesDeliveryNote, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='stock_movements'
    )
    sales_return = models.ForeignKey(
        'SalesReturn',
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
        verbose_name = "Sales Stock Movement"
        verbose_name_plural = "Sales Stock Movements"
    
    def __str__(self):
        return f"{self.movement_type} - {self.stock.item.name} - {self.quantity}"



class SalesReturn(models.Model):
    """Represents a sales return / credit note for a SalesInvoice."""
    sales_invoice = models.ForeignKey(SalesInvoice, related_name='returns', on_delete=models.CASCADE)
    return_number = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField(default=timezone.now)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    shipped_by = models.CharField(max_length=255, blank=True, null=True)
    courier_name = models.CharField(max_length=255, blank=True, null=True)
    tracking_number = models.CharField(max_length=255, blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    stock_updated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SR-{self.return_number} for {self.sales_invoice.inv_number}"

    def save(self, *args, **kwargs):
        if not self.return_number:
            last = SalesReturn.objects.order_by('-id').first()
            if last and last.return_number:
                try:
                    last_no = int(last.return_number.split('-')[-1])
                    self.return_number = f"SR-{last_no + 1:05d}"
                except Exception:
                    self.return_number = "SR-00001"
            else:
                self.return_number = "SR-00001"
        super().save(*args, **kwargs)


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, related_name='items', on_delete=models.CASCADE)
    invoice_item = models.ForeignKey(SalesInvoiceItem, on_delete=models.CASCADE)
    quantity_returned = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Return {self.sales_return.return_number} - {self.invoice_item.product.name}: {self.quantity_returned}"



class PerformaInvoicePrefix(models.Model):
    prefix = models.CharField(max_length=10, unique=True, verbose_name="Prefix")

    def __str__(self):
        return self.prefix


class PerformaInvoice(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    inv_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=timezone.now)
    sales_person = models.ForeignKey(SalesPerson, on_delete=models.CASCADE, null=True, blank=True)
    payment_term = models.ForeignKey('PayTerms.PayTerms', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    discount_value = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')], default='flat')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    fx_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text='Exchange rate from invoice currency to company base currency.',
    )
    document_currency = models.ForeignKey(
        'currencies.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performa_invoices',
    )
    fx_rate_date = models.DateField(null=True, blank=True)
    total_amount_base = models.DecimalField(default=Decimal('0.00'), max_digits=18, decimal_places=2)
    turnover_tax = models.ForeignKey(
        'Tax.Tax',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performa_invoices_turnover_tax',
    )
    place_of_supply = models.CharField(max_length=100, blank=True, null=True, verbose_name="Place of Supply")

    shipping_attention = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Attention To")
    shipping_email = models.EmailField(blank=True, null=True, verbose_name="Shipping Email")
    shipping_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Phone")
    shipping_country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping Country")
    shipping_address1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 1")
    shipping_address2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")
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
    def __str__(self):
        return f"{self.inv_number}"

    def get_currency_symbol(self):
        """Returns the appropriate currency symbol for this invoice."""
        if self.document_currency:
            return self.document_currency.symbol or self.document_currency.code or '₹'
        
        # Fallback to customer's default currency if document currency is not set
        if self.customer and hasattr(self.customer, 'currency') and self.customer.currency:
            try:
                from currencies.models import Currency
                customer_cur = Currency.objects.filter(code__iexact=self.customer.currency).first()
                if customer_cur:
                    return customer_cur.symbol or customer_cur.code or '₹'
                return self.customer.currency
            except Exception:
                return '₹'
        
        return '₹'



class PerformaInvoiceItem(models.Model):
    performa_inv = models.ForeignKey(PerformaInvoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    prd_brcd = models.CharField(max_length=100, blank=True, null=True)
    prd_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    prd_taxgroup = models.CharField(max_length=255, null=True, blank=True)
    prd_disvalue = models.DecimalField(default=Decimal('0.00'), max_digits=12, decimal_places=2, blank=True, null=True)
    prd_distype = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6) # Document currency price
    o_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0.000000')) # Base currency price
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class EWayBill(models.Model):
    TRANSPORT_MODE_CHOICES = [
        ('1', 'Road'),
        ('2', 'Rail'),
        ('3', 'Air'),
        ('4', 'Ship'),
    ]
    VEHICLE_TYPE_CHOICES = [
        ('R', 'Regular'),
        ('O', 'ODC (Over Dimensional Cargo)'),
    ]
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('submitted', 'Submitted to NIC'),
        ('generated', 'Generated'),
        ('cancelled', 'Cancelled'),
    ]

    # ── Link to SalesInvoice ──────────────────────────────────────────────────
    invoice = models.OneToOneField(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name='eway_bill',
    )

    ewb_number = models.CharField(max_length=20, blank=True, null=True,
                                  verbose_name='E-Way Bill Number')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # ── GSTIN / Party ─────────────────────────────────────────────────────────
    # auto-filled from invoice  →  company.tax_id  and  customer.gst_number
    gstin_from = models.CharField(max_length=15, blank=True, verbose_name='GSTIN (Supplier)')
    gstin_to   = models.CharField(max_length=15, blank=True, verbose_name='GSTIN (Recipient)')

    # ── Place details ─────────────────────────────────────────────────────────
    place_from   = models.CharField(max_length=100, blank=True, verbose_name='From City')
    place_to     = models.CharField(max_length=100, blank=True, verbose_name='To City')
    pincode_from = models.CharField(max_length=6,   blank=True, verbose_name='From Pincode')
    pincode_to   = models.CharField(max_length=6,   blank=True, verbose_name='To Pincode')
    state_from   = models.CharField(max_length=50,  blank=True, verbose_name='From State')
    state_to     = models.CharField(max_length=50,  blank=True, verbose_name='To State')

    # ── Transport details (filled by user) ───────────────────────────────────
    mode_of_transport  = models.CharField(max_length=1, choices=TRANSPORT_MODE_CHOICES, default='1')
    vehicle_number     = models.CharField(max_length=15, blank=True, verbose_name='Vehicle Number')
    vehicle_type       = models.CharField(max_length=1,  choices=VEHICLE_TYPE_CHOICES, default='R')
    transporter_id     = models.CharField(max_length=15, blank=True, verbose_name='Transporter ID')
    transporter_name   = models.CharField(max_length=100, blank=True)
    transport_doc_no   = models.CharField(max_length=30,  blank=True, verbose_name='Transport Doc No.')
    transport_doc_date = models.DateField(null=True, blank=True, verbose_name='Transport Doc Date')

    # ── Goods summary ─────────────────────────────────────────────────────────
    total_value          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hsn_code             = models.CharField(max_length=8, blank=True, verbose_name='Primary HSN Code')
    approximate_distance = models.IntegerField(default=0, verbose_name='Approx. Distance (km)')

    # ── Timestamps ───────────────────────────────────────────────────────────
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # ── API Response data (from NIC) ──────────────────────────────────────────
    valid_upto = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Valid Upto',
        help_text='Expiry date/time returned by NIC API'
    )
    alert = models.TextField(
        blank=True,
        verbose_name='API Alert/Warning',
        help_text='Warnings or notes from NIC API response'
    )
    api_raw_response = models.JSONField(
        null=True, blank=True,
        verbose_name='Raw API Response',
        help_text='Full JSON response from NIC stored for audit trail'
    )
    cancel_reason_code = models.CharField(
        max_length=2, blank=True,
        verbose_name='Cancel Reason Code',
        choices=[('1','Duplicate'),('2','Order Cancelled'),('3','Data Entry Mistake'),('4','Others')],
    )
    cancel_remarks = models.CharField(
        max_length=200, blank=True,
        verbose_name='Cancel Remarks',
        help_text='Reason provided when cancelling'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name       = 'E-Way Bill'
        verbose_name_plural = 'E-Way Bills'

    def __str__(self):
        return f"EWB-{self.ewb_number or 'DRAFT'} | {self.invoice.inv_number}"


# ──────────────────────────────────────────────────────────────────────────────
# Fernet-based field encryption helper
# ──────────────────────────────────────────────────────────────────────────────

def _get_fernet():
    """Get Fernet cipher for password encryption."""
    from cryptography.fernet import Fernet
    from django.conf import settings
    key = getattr(settings, "EWAY_BILL_ENCRYPT_KEY", None)
    if not key:
        raise ValueError(
            "EWAY_BILL_ENCRYPT_KEY missing from settings. "
            "Generate with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(plaintext: str) -> str:
    """Encrypt plaintext using Fernet."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt ciphertext using Fernet."""
    if not ciphertext:
        return ""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def _default_app_key() -> str:
    """Generate a new app key for each EWayBillCredential instance."""
    return get_random_string(32)


# ──────────────────────────────────────────────────────────────────────────────
# EWayBillCredential – one per company
# ──────────────────────────────────────────────────────────────────────────────

class EWayBillCredential(models.Model):
    """
    Stores NIC E-Way Bill API login credentials for a Company.
    Passwords are Fernet-encrypted at rest.
    """

    company = models.OneToOneField(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='ewb_credential',
    )
    gstin = models.CharField(max_length=15, verbose_name="GSTIN")
    username = models.CharField(max_length=100, verbose_name="NIC Portal Username")

    # Encrypted fields
    _password = models.CharField(
        max_length=500,
        db_column="password",
        verbose_name="Password (encrypted)",
        blank=True,
        default="",
    )
    app_key = models.CharField(
        max_length=32,
        default=_default_app_key,
        verbose_name="App Key (32-char AES session key)",
        help_text="Auto-generated. Do not share.",
    )
    nic_public_key = models.TextField(
        verbose_name="NIC Public Key (PEM)",
        help_text="Paste the RSA public key from https://ewaybillgst.gov.in/apidoc/ here.",
        blank=True,
    )

    is_sandbox = models.BooleanField(
        default=False,
        verbose_name="Use Sandbox (testing)",
        help_text="Enable for testing; disable for production.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "E-Way Bill Credential"
        verbose_name_plural = "E-Way Bill Credentials"

    def __str__(self):
        return f"EWB Creds – {self.gstin} ({self.company})"

    def set_password(self, raw_password: str):
        """Encrypt and store a raw password."""
        self._password = _encrypt(raw_password)

    def get_password(self) -> str:
        """Decrypt and return the stored password."""
        return _decrypt(self._password)

    def regenerate_app_key(self):
        """Generate a new app key (session key)."""
        self.app_key = get_random_string(32)
        self.save(update_fields=["app_key", "updated_at"])


