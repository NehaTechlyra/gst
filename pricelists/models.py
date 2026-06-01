from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class PriceList(models.Model):
    PRICE_TYPE_CHOICES = [
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
    ]
    ROUNDING_CHOICES = [
        ('none', 'No Rounding'),
        ('nearest', 'Round to Nearest'),
        ('up', 'Round Up'),
        ('down', 'Round Down'),
    ]
    PRICING_SCHEME_CHOICES = [
        ('percentage', 'All Items (Percentage)'),
        ('individual', 'Individual Items (Custom Rate)'),
    ]
    PERCENTAGE_TYPE_CHOICES = [
        ('markup', 'Markup'),
        ('markdown', 'Markdown'),
    ]

    name = models.CharField(max_length=255, unique=True)
    price_type = models.CharField(max_length=10, choices=PRICE_TYPE_CHOICES, default='sales')
    pricing_scheme = models.CharField(
        max_length=20,
        choices=PRICING_SCHEME_CHOICES,
        default='individual',
        help_text="Choose whether this applies a global percentage or individual line rates",
    )
    percentage_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    percentage_type = models.CharField(max_length=10, choices=PERCENTAGE_TYPE_CHOICES, null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    rounding = models.CharField(max_length=10, choices=ROUNDING_CHOICES, default='none')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'erp_price_lists'
        ordering = ['-created_at']
        verbose_name = 'Price List'
        verbose_name_plural = 'Price Lists'

    def __str__(self):
        return f"{self.name} ({self.get_price_type_display()})"

    @property
    def is_valid(self):
        today = timezone.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        return self.is_active

    def get_item_count(self):
        return self.price_list_items.count()


class PriceListItem(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount'),
        ('custom', 'Custom Price'),
    ]

    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name='price_list_items'
    )
    item_name = models.CharField(max_length=255)
    item_sku = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    base_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    discount_type = models.CharField(
        max_length=15, choices=DISCOUNT_TYPE_CHOICES, default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    custom_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    min_quantity = models.PositiveIntegerField(default=1)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'erp_price_list_items'
        ordering = ['item_name']
        unique_together = ('price_list', 'item_sku')
        verbose_name = 'Price List Item'
        verbose_name_plural = 'Price List Items'

    def __str__(self):
        return f"{self.item_name} - {self.price_list.name}"

    @property
    def final_price(self):
        if self.discount_type == 'custom' and self.custom_price is not None:
            return self.custom_price
        elif self.discount_type == 'percentage':
            discount = self.base_price * (self.discount_value / 100)
            return round(self.base_price - discount, 2)
        elif self.discount_type == 'fixed':
            return max(0, self.base_price - self.discount_value)
        return self.base_price

    @property
    def discount_display(self):
        if self.discount_type == 'percentage':
            return f"{self.discount_value}%"
        elif self.discount_type == 'fixed':
            return f"-{self.discount_value}"
        return "Custom"


class ContactPriceList(models.Model):
    """Assigns a price list to a contact (customer/vendor)"""
    contact_name = models.CharField(max_length=255)
    contact_type = models.CharField(
        max_length=10,
        choices=[('customer', 'Customer'), ('vendor', 'Vendor')],
        default='customer'
    )
    price_list = models.ForeignKey(
        PriceList, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_contacts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'erp_contact_price_lists'
        verbose_name = 'Contact Price List'
        verbose_name_plural = 'Contact Price Lists'

    def __str__(self):
        return f"{self.contact_name} → {self.price_list}"
