from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from company.models import Company


class Currency(models.Model):
    """
    Organisation currency master: ISO code, display, decimals, base flag.
    One row per (company, code). Exactly one currency per company should have is_base=True.
    """
    FORMAT_CHOICES = [
        ("1,234.56", "1,234.56"),
        ("1.234,56", "1.234,56"),
        ("1 234,56", "1 234,56"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="currencies")
    code = models.CharField(max_length=3, help_text="ISO 4217 code, e.g. INR, USD")
    symbol = models.CharField(max_length=8, blank=True, default="")
    name = models.CharField(max_length=80, blank=True, default="")
    decimal_places = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
    )
    display_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="1,234.56")
    is_base = models.BooleanField(default=False, help_text="Organisation functional/base currency")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_id", "code"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="uniq_currency_company_code"),
        ]
        verbose_name_plural = "Currencies"

    def __str__(self):
        # Display only the ISO code for cleaner select labels (remove company id)
        return f"{self.code}"


class ExchangeRate(models.Model):
    """
    Rate from foreign currency to base: 1 unit of this currency = rate units of base currency.
    Effective from start date until superseded by a later row.
    """
    SOURCE_FEED = "feed"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_FEED, "Exchange feed"),
        (SOURCE_MANUAL, "Manual"),
    ]

    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="exchange_rates",
    )
    effective_from = models.DateField(db_index=True)
    rate = models.DecimalField(
        max_digits=24,
        decimal_places=10,
        validators=[MinValueValidator(Decimal("0.0000000001"))],
        help_text="Base currency amount for 1 unit of this foreign currency",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["currency_id", "-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["currency", "effective_from"],
                name="uniq_exchange_rate_currency_date",
            ),
        ]

    def __str__(self):
        return f"{self.currency.code} @ {self.effective_from}: {self.rate}"
