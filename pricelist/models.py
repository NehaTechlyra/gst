from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class PriceList(models.Model):
    TYPE_CHOICES = [
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
    ]
    ROUNDING_CHOICES = [
        ('none', 'No Rounding'),
        ('nearest', 'Round to Nearest'),
        ('up', 'Round Up'),
        ('down', 'Round Down'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    currency = models.CharField(max_length=10, default='USD')
    rounding = models.CharField(max_length=10, choices=ROUNDING_CHOICES, default='none')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'price_lists'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def is_valid(self):
        today = timezone.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        return self.is_active


class PriceListItem(models.Model):
    PRICING_METHOD_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Price'),
    ]
    ADJUSTMENT_TYPE_CHOICES = [
        ('markup', 'Markup (Increase)'),
        ('markdown', 'Markdown (Decrease)'),
    ]

    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name='items'
    )
    # References your existing Item model — adjust app_label as needed
    item = models.ForeignKey(
        'Items.Item',  # Change 'inventory' to your actual app name
        on_delete=models.CASCADE,
        related_name='price_list_items'
    )
    pricing_method = models.CharField(max_length=15, choices=PRICING_METHOD_CHOICES)
    # For percentage method
    adjustment_type = models.CharField(
        max_length=10, choices=ADJUSTMENT_TYPE_CHOICES, null=True, blank=True
    )
    percentage = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    # For fixed method
    custom_rate = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'price_list_items'
        unique_together = ('price_list', 'item')

    def __str__(self):
        return f"{self.price_list.name} - {self.item.name}"

    def get_computed_price(self):
        """Returns the final price based on the item's base rate and pricing method."""
        base_rate = self.item.rate  # Adjust field name if needed
        if self.pricing_method == 'fixed':
            return self.custom_rate
        elif self.pricing_method == 'percentage' and self.percentage is not None:
            adjustment = base_rate * (self.percentage / 100)
            if self.adjustment_type == 'markup':
                return base_rate + adjustment
            else:
                return base_rate - adjustment
        return base_rate


class ContactPriceList(models.Model):
    """Assigns a price list to a customer or vendor contact."""
    # References your existing Contact model — adjust app_label as needed
    contact = models.ForeignKey(
        'customer.Customer',  # Change 'contacts' to your actual app name
        on_delete=models.CASCADE,
        related_name='price_list_assignments'
    )
    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name='contact_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_price_lists'
        unique_together = ('contact', 'price_list')

    def __str__(self):
        return f"{self.contact} → {self.price_list.name}"
