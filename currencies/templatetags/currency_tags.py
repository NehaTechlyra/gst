from django import template

from currencies.utils import format_amount, get_decimal_places

register = template.Library()


@register.filter(name="currency_amount")
def currency_amount(value, currency=None):
    """
    Format `value` using the decimal places configured for `currency`.

    `currency` may be a Currency instance, an ISO code string (e.g. "JPY"),
    or omitted/None (falls back to 2 decimal places, same as floatformat:2).

    Usage in templates (drop-in replacement for floatformat:2 on money fields):
        {{ invoice.total_amount|currency_amount:document_currency }}
        {{ item.price|currency_amount:document_currency_code }}
        {{ payment.amount|currency_amount:base_currency }}
    """
    return format_amount(value, currency)


@register.filter(name="currency_decimal_places")
def currency_decimal_places(currency):
    """Return the integer decimal-place count for a Currency instance or ISO code."""
    return get_decimal_places(currency)
