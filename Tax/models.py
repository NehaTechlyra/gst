from django.db import models
from django.conf import settings 
from django.core.validators import MinValueValidator
from decimal import Decimal

class TaxType(models.Model):
    name = models.CharField(max_length=50)   # CGST, SGST, VAT
    #

    def __str__(self):
        return f"{self.name}"
    
class Tax(models.Model):
    TAX_TYPE_CHOICES = [
        ('GST', 'GST'),
        ('VAT', 'VAT'),
        ('SALES', 'Sales Tax'),
        ('TURNOVER', 'Turnover Tax'),
        ('NONE', 'None'),
        ('LOCAL', 'Local Tax'),
    ]
    TAX_SCOPE_CHOICES = [
        ('SALES', 'Sales'),
        ('PURCHASE', 'Purchase'),
        ('BOTH', 'Both'),
        
    ]
    TAX_METHOD_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed'),
    ]
    APPLICABLE_ON_CHOICES = [
       
        
        ('Total Amount', 'Total Amount'),
        ('TAX', 'Tax'),
    ]
    taxname = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True, null=True)
    # taxtype = models.ForeignKey(TaxType, on_delete=models.CASCADE)
    taxtype = models.ForeignKey(TaxType, on_delete=models.SET_NULL, null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    country = models.CharField(max_length=100, blank=True, null=True)
    tax_type = models.CharField(max_length=10, choices=TAX_TYPE_CHOICES, default='GST')
    tax_scope = models.CharField(max_length=10, choices=TAX_SCOPE_CHOICES, default='SALES')
    # tax_method = models.CharField(max_length=20, choices=TAX_METHOD_CHOICES, default='PERCENTAGE')
    applicable_on = models.CharField(max_length=20, choices=APPLICABLE_ON_CHOICES, default='Total Amount')
    tax_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    status = models.BooleanField(default=True)

    # Audit fields
    crtd_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='taxes_created')
    crtd_at = models.DateTimeField(auto_now_add=True)
    updt_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='taxes_updated')
    updt_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    @property
    def model_name(self):
        return "Tax"

    @property
    def display_name(self):
        return (self.name or self.taxname or "").strip()

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.taxname
        super().save(*args, **kwargs)


class TaxComponent(models.Model):
    tax = models.ForeignKey(Tax, related_name='components', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.rate}%"


class TaxRule(models.Model):
    RULE_TYPE_CHOICES = [
        ('intra', 'Intra State'),
        ('inter', 'Inter State'),
    ]
    tax = models.ForeignKey(Tax, related_name='rules', on_delete=models.CASCADE)
    from_state = models.CharField(max_length=100, blank=True, null=True)
    to_state = models.CharField(max_length=100, blank=True, null=True)
    rule_type = models.CharField(max_length=10, choices=RULE_TYPE_CHOICES)

    def __str__(self):
        return f"{self.tax.display_name} - {self.rule_type}"

class TaxGroup(models.Model):
    group_name = models.CharField(max_length=255)
    taxes = models.ManyToManyField(Tax, blank=False)
    status = models.BooleanField(default=True)

    # Audit fields
    crtd_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='taxgroups_created')
    crtd_at = models.DateTimeField(auto_now_add=True)
    updt_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='taxgroups_updated')
    updt_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.group_name

    @property
    def model_name(self):
        return "TaxGroup"


class TaxMaster(models.Model):
    TAX_TYPE_CHOICES = [
        ('GST', 'GST'),
        ('VAT', 'VAT'),
        ('SALES', 'SALES'),
        ('TURNOVER', 'TURNOVER'),
        ('LOCAL', 'LOCAL'),
    ]

    TAX_SCOPE_CHOICES = [
        ('ITEM', 'Item'),
        ('INVOICE', 'Invoice'),
    ]

    TAX_METHOD_CHOICES = [
        ('PERCENT', 'Percent'),
        ('FIXED', 'Fixed'),
    ]

    APPLICABLE_ON_CHOICES = [
        ('ALL', 'All'),
        ('ITEM', 'Item'),
        ('CATEGORY', 'Category'),
    ]

    tax_id = models.AutoField(primary_key=True)
    tax_name = models.CharField(max_length=255)
    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, default='GST')
    tax_scope = models.CharField(max_length=10, choices=TAX_SCOPE_CHOICES)
    tax_rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax_method = models.CharField(max_length=10, choices=TAX_METHOD_CHOICES)
    applicable_on = models.CharField(max_length=10, choices=APPLICABLE_ON_CHOICES, default='ALL')
    tax_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='tax_master_items')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tax_master'
        ordering = ['tax_order', 'tax_name']

    def __str__(self):
        return self.tax_name


class TdsTcsBase(models.Model):
    INCOME_TAX_ACT_CHOICES = [
        ('new-2025', 'New Income Tax Act 2025'),
        ('old-1961', 'Income Tax Act 1961'),
    ]
    SECTION_CHOICES = [
        ('194c', 'Section 194C'),
        ('194j', 'Section 194J'),
        ('194q', 'Section 194Q'),
        ('192', 'Section 192'),
    ]

    tax_id = models.AutoField(primary_key=True)
    tax_name = models.CharField(max_length=255)
    tax_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    income_tax_act = models.CharField(max_length=50, choices=INCOME_TAX_ACT_CHOICES, blank=True, null=True)
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, blank=True, null=True)
    higher_rate = models.BooleanField(default=False)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TdsMaster(TdsTcsBase):
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='tds_master_items')

    class Meta:
        db_table = 'tds_master'
        ordering = ['tax_name']

    def __str__(self):
        return self.tax_name


class TcsMaster(TdsTcsBase):
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='tcs_master_items')

    class Meta:
        db_table = 'tcs_master'
        ordering = ['tax_name']

    def __str__(self):
        return self.tax_name


