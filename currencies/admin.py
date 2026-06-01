from django.contrib import admin

from .models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "company", "symbol", "is_base", "is_active", "decimal_places")
    list_filter = ("is_base", "is_active")
    search_fields = ("code", "name", "company__name")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "effective_from", "rate", "source")
    list_filter = ("source",)
    date_hierarchy = "effective_from"
