from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


ROUNDING_NONE = "none"
ROUNDING_WHOLE = "whole"
ROUNDING_INCREMENT = "increment"


def to_money(value):
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def apply_sales_rounding(amount, company=None):
    amount = to_money(amount)
    method = (getattr(company, "sales_rounding_method", ROUNDING_NONE) or ROUNDING_NONE).strip().lower()

    if method == ROUNDING_WHOLE:
        rounded = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    elif method == ROUNDING_INCREMENT:
        increment = to_money(getattr(company, "sales_rounding_increment", 0))
        if increment <= 0:
            rounded = amount
        else:
            rounded = (amount / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment
    else:
        rounded = amount

    rounded = rounded.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    adjustment = (rounded - amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return rounded, adjustment
