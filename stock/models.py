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


class StockMovement(models.Model):
    """
    Audit trail for manual stock movements initiated from the Stock app itself:
    quantity adjustments and warehouse-to-warehouse transfers.

    Movements that originate from other modules (goods received / purchase
    returns, sales deliveries / sales returns) already have their own audit
    trail models -- Purchase.StockMovement and sales.SalesStockMovement -- and
    are not duplicated here. stock/views.get_combined_movements() merges all
    three sources into a single chronological view for reporting.
    """
    MOVEMENT_TYPE_CHOICES = [
        ('adjustment_in', 'Adjustment In'),
        ('adjustment_out', 'Adjustment Out'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]

    REFERENCE_TYPE_CHOICES = [
        ('manual_adjustment', 'Manual Adjustment'),
        ('warehouse_transfer', 'Warehouse Transfer'),
    ]

    stock = models.ForeignKey(
        'stock.Stock',
        related_name='stock_movements',
        on_delete=models.CASCADE,
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Always a positive magnitude; direction is given by movement_type",
    )

    reference_type = models.CharField(max_length=30, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.PositiveIntegerField(blank=True, null=True)

    # For transfers, points at the paired in/out movement on the other warehouse's stock row
    linked_movement = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='paired_with',
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='stock_movements_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who recorded this movement",
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.stock.item.name} - {self.quantity}"
