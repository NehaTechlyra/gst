import math
from decimal import Decimal
from django.db.models import Q
from pricelists.models import PriceList, PriceListItem

def get_calculated_item_price(price_list_id, item_sku, quantity=1, fallback_base_price=None):
    """
    Calculates the final item price based on the selected price list.
    If the price list is percentage-based, applies it to fallback_base_price.
    Returns: 
        (final_price, base_price, discount_type, discount_value)
    """
    try:
        price_list = PriceList.objects.get(pk=price_list_id)
    except PriceList.DoesNotExist:
        if fallback_base_price is None: fallback_base_price = Decimal('0.00')
        return Decimal(str(fallback_base_price)), Decimal(str(fallback_base_price)), None, Decimal('0.00')

    # First check for individual item override or if scheme is individual
    qs = PriceListItem.objects.filter(price_list_id=price_list_id, item_sku=item_sku, min_quantity__lte=quantity)
    item = None
    for p_item in qs.order_by('-min_quantity'):
        if p_item.max_quantity is None or p_item.max_quantity >= quantity:
            item = p_item
            break

    if item:
        return item.final_price, item.base_price, item.discount_type, item.discount_value

    if price_list.pricing_scheme == 'percentage':
        if fallback_base_price is None:
            fallback_base_price = Decimal('0.00')
        else:
            fallback_base_price = Decimal(str(fallback_base_price))

        percentage = price_list.percentage_value or Decimal('0.00')
        discount_amount = fallback_base_price * (percentage / Decimal('100.00'))

        if price_list.percentage_type == 'markup':
            final_price = fallback_base_price + discount_amount
        else:
            final_price = fallback_base_price - discount_amount

        # Handle rounding
        if price_list.rounding == 'nearest':
            final_price = Decimal(round(float(final_price)))
        elif price_list.rounding == 'up':
            final_price = Decimal(math.ceil(float(final_price)))
        elif price_list.rounding == 'down':
            final_price = Decimal(math.floor(float(final_price)))
        else:
            final_price = final_price.quantize(Decimal('0.01'))

        return final_price, fallback_base_price, 'percentage_scheme', percentage

    # If scheme is individual but item not found in price list, just return fallback
    if fallback_base_price is None:
        fallback_base_price = Decimal('0.00')
    else:
        fallback_base_price = Decimal(str(fallback_base_price))
    
    return fallback_base_price, fallback_base_price, None, Decimal('0.00')
