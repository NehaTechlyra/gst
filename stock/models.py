from django.db import models
from django.conf import settings
from decimal import Decimal

class Stock(models.Model):
    item = models.ForeignKey('Items.Item', on_delete=models.CASCADE, related_name='stocks')  # Link to item/product
    warehouse = models.ForeignKey('warehouse.Warehouse', on_delete=models.CASCADE, related_name='warehouses')  # Link to warehouse
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Quantity in stock
    batch_number = models.CharField(max_length=100, blank=True, null=True)  # Optional batch info
    serial_number = models.CharField(max_length=100, blank=True, null=True)  # Optional serial
    expiration_date = models.DateField(blank=True, null=True)  # Optional expiry
    opening_stock = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    blank=True,
    null=True,
    verbose_name='Opening Stock',
    help_text="Initial opening stock for this item in this warehouse"
    )

    status = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='stocks_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this stock"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='stocks_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this stock"
    )

    class Meta:
        unique_together = ('item', 'warehouse', 'batch_number', 'serial_number')
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"

    def __str__(self):
        return f"{self.item} - {self.warehouse} : {self.quantity}"
