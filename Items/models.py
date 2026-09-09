from django.db import models
from django.conf import settings 
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from Tax.models import Tax, TaxGroup

# class TaxGroup(models.Model):
#     group_name = models.CharField(max_length=255)
#     class Meta:
#         db_table = 'tax_taxgroup'   # force Django to use your existing table

#     def __str__(self):
#         return self.group_name

# class Tax(models.Model):
#     taxname = models.CharField(max_length=255)
#     taxtype = models.CharField(max_length=5)

#     class Meta:
#         db_table = 'tax_tax'   # use your existing table

#     def __str__(self):
#         return self.taxname

# Create your models here.
class HSNCode(models.Model):
    code = models.CharField(max_length=10, unique=True, help_text="HSN Code, e.g. 0101")
    description = models.TextField(help_text="Description of the product associated with this HSN code")

    def __str__(self):
        return f"{self.code} - {self.description[:50]}..."

class SACCode(models.Model):
    code = models.CharField(max_length=10, unique=True, help_text="SAC Code, e.g. 0101")
    description = models.TextField(help_text="Description of the product associated with this SAC code")

    def __str__(self):
        return f"{self.code} - {self.description[:50]}..."

# class Unit(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     unit_name = models.CharField(max_length=100)
#     status = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)  # Use auto_now_add if you want Django to handle timestamps
#     updated_at = models.DateTimeField(auto_now=True)      # Use auto_now to update on each save
#     created_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='units_created'
#     )
#     updated_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='units_updated'
#     )

#     class Meta:
#         db_table = 'unit_unit'   # Map to existing table

#     def __str__(self):
#         return self.unit_name
# class Uom(models.Model):  # Capital U
#     name = models.CharField(max_length=100)

#     def __str__(self):
#         return self.name



    
class Item(models.Model):
    TYPE_CHOICES = [
        ('goods', 'Goods'),
        ('service', 'Service'),
    ]
    name = models.CharField(max_length=255, blank=False, null=False)
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='goods'  # ✅ gives Django a value for old rows
    )
    unit = models.CharField(max_length=50, blank=False, null=False, default='pcs')
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    tax_pref = models.CharField(
        max_length=20,
        choices=[('taxable', 'Taxable'), ('non_taxable', 'Non-Taxable')],
        default='taxable'  # ✅ also gives a default
    )
    selling_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    sales_account = models.CharField(max_length=255, null=True, blank=True)
    sales_desc = models.TextField(blank=True, null=True)

    cost_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    purchase_account = models.CharField(max_length=255, null=True, blank=True)
    purchase_desc = models.TextField(blank=True, null=True)

    preferred_vendor = models.ForeignKey('Purchase.Vendor', on_delete=models.SET_NULL, null=True, blank=True)

    track_inventory = models.BooleanField(default=False)
    taxincld_slprice = models.BooleanField(default=False)
    taxincld_costprice = models.BooleanField(default=False)
    
    # real_slprice = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # real_costprice = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)




     # --- Newly added fields ---
    INVENTORY_ACCOUNT_CHOICES = [
        ('inv_asset', 'Inventory Asset'),
    ]
    inv_acc = models.CharField(
        max_length=50,
        choices=INVENTORY_ACCOUNT_CHOICES,
        default='inv_asset',
        blank=True,
        null=True,
        verbose_name='Inventory Account',
    )
    
    VALUATION_METHOD_CHOICES = [
        ('FIFO', 'FIFO (First In First Out)'),
        ('WAC', 'WAC (Weighted Average Cost)'),
    ]
    inv_method = models.CharField(
        max_length=10,
        choices=VALUATION_METHOD_CHOICES,
        default='FIFO',
        blank=True,
        null=True,
        verbose_name='Inventory Valuation Method',
    )
    
    op_stock = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name='Opening Stock',
    )
    op_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Opening Stock Rate per Unit',
    )
    intra_tax = models.ForeignKey(
        'Tax.TaxGroup',  # assuming your app name is 'tax'
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Intra State Tax Rate"
    )

    inter_tax_group = models.ForeignKey(
        'Tax.Tax',  # assuming your app name is 'tax'
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Inter State Tax Rate"
    )

    # For SALES companies: separate tax for sales vs purchase
    sales_tax = models.ForeignKey(
        'Tax.Tax',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_sales_tax',
        verbose_name="Sales Tax Rate",
    )
    purchase_tax = models.ForeignKey(
        'Tax.Tax',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_purchase_tax',
        verbose_name="Purchase Tax Rate",
    )
    main_barcode = models.ForeignKey(
        'Barcode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_barcode_item'
    )
    brand = models.ForeignKey(
    'brand.Brand',   # format: 'app_name.ModelName'
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='Brand',
    related_name='items'
    )
    category = models.ForeignKey(
    'category.Category',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='Category',
    related_name='items'
    )
    subcategory = models.ForeignKey(
    'category.Subcategory',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='Subcategory',
    related_name='items'
    )
    item_type = models.ForeignKey(
    'type.Type',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='Item Type',
    related_name='items'
    )
    sac_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="SAC Code ID",
        help_text="Store SAC Code ID from items_saccode table"
    )
    sales_info = models.BooleanField(default=False, verbose_name="Sales Information")
    purchase_info = models.BooleanField(default=False, verbose_name="Purchase Information")
    # -------min_stock field aded by sree on 07-03-2026------
    min_stock = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Minimum Stock Level',
        help_text='For Load low stock prefferred vendor items'
    )

    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)    # for creation timestamp
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='items_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this item"
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='items_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this item"
    )
    def __str__(self):
        return self.name

    @property
    def hsn_code_obj(self):
        if self.hsn_code:
            return HSNCode.objects.filter(id=self.hsn_code).first()
        return None

    @property
    def sac_code_obj(self):
        if self.sac_code:
            return SACCode.objects.filter(id=self.sac_code).first()
        return None

    @property
    def unit_name(self):
        if self.unit:
            try:
                # If unit is an ID, fetch from unit.Unit
                u_id = int(self.unit)
                from unit.models import Unit
                uom = Unit.objects.filter(id=u_id).first()
                if uom:
                    return uom.unit_name
            except (ValueError, TypeError, ImportError):
                pass
            return self.unit
        return "N/A"

    @property
    def barcode(self):
        return self.main_barcode.barcode if self.main_barcode else ''
    @property
    def total_tax_rate(self):
        """Sum of all tax rates under intra_tax"""
        if self.intra_tax:
            return self.intra_tax.taxes.aggregate(total=Sum("rate"))["total"] or Decimal("0.00")
        return Decimal("0.00")

    @property
    def display_cost_price(self):
        """Return cost price including tax if needed"""
        if self.taxincld_costprice:  # already includes GST
            return self.cost_price or Decimal("0.00")
        else:
            rate = self.total_tax_rate
            return (self.cost_price or Decimal("0.00")) * (1 + rate / Decimal("100"))

    @property
    def display_selling_price(self):
        """Return selling price including tax if needed"""
        if self.taxincld_slprice:
            return self.selling_price or Decimal("0.00")
        else:
            rate = self.total_tax_rate
            return (self.selling_price or Decimal("0.00")) * (1 + rate / Decimal("100"))



class Barcode(models.Model):
    item = models.ForeignKey('Items.Item', on_delete=models.CASCADE, related_name='barcodes')
    barcode = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.barcode} ({self.item.name})"

class Uom(models.Model):
    item = models.ForeignKey('Items.Item', on_delete=models.CASCADE, related_name='uoms')
    # name = models.CharField(max_length=100)
    name = models.ForeignKey('Items.Uom_name', on_delete=models.CASCADE, related_name='uoms')
    # uom = models.ForeignKey('unit.Unit', on_delete=models.PROTECT)  # or Uom if using that
    conversion_factor = models.DecimalField(max_digits=10, decimal_places=3, default=1.000)
    barcode = models.ForeignKey(Barcode, on_delete=models.SET_NULL, null=True, blank=True, related_name='uom_references')

    def __str__(self):
        return f"{self.item.name} - {self.name} (×{self.conversion_factor})"

class Uom_name(models.Model):
    
    name = models.CharField(max_length=100)
