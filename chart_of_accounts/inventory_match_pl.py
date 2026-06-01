"""
████████████████████████████████████████████████████████████████████████████
INVENTORY VALUATION LOGIC — P&L MATCHING MODE
████████████████████████████████████████████████████████████████████████████

This module provides functions to calculate inventory valuation that aligns
with the Profit & Loss statement's "Stock In Hand" ledger balance.

Formula: Closing = Opening + Purchases + Adjustments - COGS
"""

from decimal import Decimal, ROUND_HALF_UP
from Items.models import Item
from stock.models import Stock
from Purchase.models import BillItem
from sales.models import SalesInvoice, SalesInvoiceItem
from journal.models import JournalLine
from chart_of_accounts.models import ChartOfAccounts
from django.db.models import Sum, F, Q
from django.db import models
import logging

logger = logging.getLogger(__name__)


def get_item_cost_rate(item, to_date=None):
    """
    Get the best estimated cost rate for an item as of a date.
    1. Try op_rate from master.
    2. Try most recent purchase price.
    """
    try:
        opening_rate = Decimal('0')
        if item.op_rate:
            opening_rate = Decimal(str(item.op_rate))
            if item.taxincld_costprice:
                total_tax_rate = Decimal('0.00')
                if item.intra_tax:
                    try:
                        tax_sum = item.intra_tax.taxes.aggregate(Sum('rate'))['rate__sum']
                        if tax_sum:
                            total_tax_rate = Decimal(str(tax_sum))
                    except Exception:
                        pass
                if total_tax_rate > Decimal('0.00'):
                    multiplier = Decimal('1.00') + (total_tax_rate / Decimal('100.00'))
                    opening_rate = opening_rate / multiplier
        
        if opening_rate == 0:
            recent_bill_qs = BillItem.objects.filter(product=item)
            if to_date:
                recent_bill_qs = recent_bill_qs.filter(bill__date__lte=to_date)
            recent_bill_item = recent_bill_qs.order_by('-bill__date', '-id').first()
            if recent_bill_item and recent_bill_item.price:
                opening_rate = Decimal(str(recent_bill_item.price))
        
        return opening_rate.quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0')


def get_opening_stock_value(item, to_date=None):
    """
    Get the "True" opening stock value for an item as of to_date.
    Formula: Total Balance as of (to_date-1) - Cumulative Adjustments as of (to_date-1).
    """
    if to_date is None:
        _, val = _get_static_master_data(item)
        return val
    
    from datetime import timedelta
    if isinstance(to_date, str):
        from datetime import datetime
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    else:
        to_date_obj = to_date
    
    day_before = to_date_obj - timedelta(days=1)
    
    # 1. Total balance as of day before
    _, total_val_as_of = calculate_inventory_value_matching_pl(item, from_date=None, to_date=day_before)
    
    # 2. Cumulative adjustments as of day before
    cum_adj = get_stock_adjustments_value(item, from_date=None, to_date=day_before)
    
    # 3. True Opening = Total - Adjustments
    return (total_val_as_of - cum_adj).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _get_static_master_data(item, as_of_date=None):
    """
    Internal helper for static master opening data (qty, val).
    Prioritizes 'Opening Balance Equity' journals, then falls back to Master.
    If it's an Adjustment journal, returns (0, 0) to avoid double-counting with Activity.
    """
    try:
        # 1. Try "True" opening from Equity-linked journals
        # If as_of_date is provided, we only count journals on or before that date.
        true_val = get_true_opening_stock_for_item(item, as_of_date)
        stock_recs = Stock.objects.filter(item=item)
        
        # We count master qty from all stock records for this item.
        # We ignore created_at because opening_stock field represents the "Beginning of Time"
        # for this item, regardless of when the record was inserted into the database.
        master_qty = sum(Decimal(str(s.opening_stock or 0)) for s in stock_recs)
        
        if true_val > 0:
            return master_qty, true_val
        
        # Avoid Double-Counting Mid-Period Journals:
        # If this item has a "True Opening" journal ANYTIME (even in the future 
        # relative to as_of_date), we MUST NOT fall back to master data.
        # Otherwise, the mid-period logic will add the journal value to the master value.
        if get_true_opening_stock_for_item(item) > 0:
            return Decimal('0.00'), Decimal('0.00')
        
        # 2. Check if an Adjustment journal exists for this item
        # If so, we assume the user intends this to be an adjustment, not opening stock.
        adj_qs = JournalLine.objects.filter(
            account__name__icontains='Stock Adjustment',
            journal__status='posted',
            status=True
        ).filter(
            Q(description__icontains=item.name) | 
            Q(journal__reference__icontains=item.name) | 
            Q(journal__narration__icontains=item.name)
        )
            
        if adj_qs.exists():
            # Return 0,0 so it's picked up by get_stock_adjustments_value instead
            return Decimal('0.00'), Decimal('0.00')
            
        # 3. Fallback to Master Data
        if not master_qty:
            return Decimal('0'), Decimal('0')
            
        rate = get_item_cost_rate(item, to_date=as_of_date)
        return master_qty, (master_qty * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0'), Decimal('0')


def get_true_opening_stock_for_item(item, opening_date=None):
    """
    Calculate the portion of Stock In Hand for this item 
    that was balanced against 'Opening Balance Equity'.
    """
    try:
        stock_account = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand', status=True).first()
        equity_account = ChartOfAccounts.objects.filter(name__icontains='Opening Balance Equity', status=True).first()
        
        if not stock_account or not equity_account:
            return Decimal('0.00')

        # Find journals that touch both Stock In Hand (for this item) and Equity
        # We check the journal narration/reference for the item name
        from django.db.models import Q
        journal_ids = JournalLine.objects.filter(
            account=equity_account,
            journal__status='posted',
            status=True
        )
        if opening_date:
            journal_ids = journal_ids.filter(journal__date__lte=opening_date)
            
        journal_ids = journal_ids.values_list('journal_id', flat=True)

        item_lines = JournalLine.objects.filter(
            account=stock_account,
            journal_id__in=journal_ids,
            status=True
        ).filter(
            Q(description__icontains=item.name) |
            Q(journal__reference__icontains=item.name) |
            Q(journal__narration__icontains=item.name)
        )
        
        totals = item_lines.aggregate(d=Sum('debit'), c=Sum('credit'))
        return Decimal(str(totals['d'] or 0)) - Decimal(str(totals['c'] or 0))
    except Exception:
        return Decimal('0.00')


def get_purchases_value(item, from_date=None, to_date=None):
    """Total purchase cost for an item in the period."""
    try:
        qs = BillItem.objects.filter(product=item).select_related('bill')
        if from_date:
            qs = qs.filter(bill__date__gte=from_date)
        if to_date:
            qs = qs.filter(bill__date__lte=to_date)
        total = Decimal('0')
        for bi in qs:
            total += Decimal(str(bi.quantity or 0)) * Decimal(str(bi.price or 0))
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0')


def get_purchases_qty(item, from_date=None, to_date=None):
    """Total purchased quantity for an item in the period."""
    try:
        qs = BillItem.objects.filter(product=item).select_related('bill')
        if from_date:
            qs = qs.filter(bill__date__gte=from_date)
        if to_date:
            qs = qs.filter(bill__date__lte=to_date)
        total_qty = Decimal('0')
        for bi in qs:
            total_qty += Decimal(str(bi.quantity or 0))
        return total_qty.quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0')


def get_sales_qty(item, from_date=None, to_date=None):
    """Total sold quantity for an item in the period."""
    try:
        qs = SalesInvoiceItem.objects.filter(product=item).select_related('sales_inv')
        if from_date:
            qs = qs.filter(sales_inv__date__gte=from_date)
        if to_date:
            qs = qs.filter(sales_inv__date__lte=to_date)
        total = qs.aggregate(total=Sum('quantity'))['total'] or 0
        return Decimal(str(total)).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0')


def get_stock_adjustments_value(item, from_date=None, to_date=None):
    """
    Get the net value of manual stock adjustments for an item from journal entries.
    Excludes bills and opening stock already counted.
    """
    try:
        stock_account = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand', status=True).first()
        if not stock_account: return Decimal('0')

        # Main query for this item's Stock In Hand journals
        qs = JournalLine.objects.filter(account=stock_account, journal__status='posted', status=True
        ).filter(
            Q(description__icontains=item.name) |
            Q(journal__reference__icontains=item.name) |
            Q(journal__narration__icontains=item.name)
        ).exclude(journal__reference__icontains='Closing'
        ).exclude(journal__reference__icontains='Opening Balances'
        ).exclude(journal__reference__icontains='COGS')

        if from_date: qs = qs.filter(journal__date__gte=from_date)
        if to_date: qs = qs.filter(journal__date__lte=to_date)

        totals = qs.aggregate(d=Sum('debit'), c=Sum('credit'))
        net_adjustment = Decimal(str(totals['d'] or 0)) - Decimal(str(totals['c'] or 0))

        # Subtract Opening Stock Journals (counted via op_rate)
        # We only subtract "True" opening stock journals (against equity)
        # We EXCLUDE "OPENING_STOCK_ADJUSTMENT" journals which should be treated as manual adjustments
        op_qs = JournalLine.objects.filter(account=stock_account, journal__status='posted', status=True
        ).filter(Q(journal__reference__icontains='OPENING_STOCK') & ~Q(journal__reference__icontains='ADJUSTMENT') & (
            Q(description__icontains=item.name) |
            Q(journal__reference__icontains=item.name) |
            Q(journal__narration__icontains=item.name)
        ))
        if from_date: op_qs = op_qs.filter(journal__date__gte=from_date)
        if to_date: op_qs = op_qs.filter(journal__date__lte=to_date)
        op_totals = op_qs.aggregate(d=Sum('debit'), c=Sum('credit'))
        opening_stock_net = Decimal(str(op_totals['d'] or 0)) - Decimal(str(op_totals['c'] or 0))

        # Subtract Bill Journals (counted via get_purchases_value)
        from Purchase.models import Bill
        bill_refs = list(Bill.objects.filter(status__in=['Open', 'Closed']).values_list('bill_number', flat=True))
        bill_stock_net = Decimal('0')
        if bill_refs:
            b_qs = JournalLine.objects.filter(account=stock_account, journal__status='posted', status=True, journal__reference__in=bill_refs
            ).filter(Q(description__icontains=item.name) | Q(journal__narration__icontains=item.name))
            if from_date: b_qs = b_qs.filter(journal__date__gte=from_date)
            if to_date: b_qs = b_qs.filter(journal__date__lte=to_date)
            b_totals = b_qs.aggregate(d=Sum('debit'), c=Sum('credit'))
            bill_stock_net = Decimal(str(b_totals['d'] or 0)) - Decimal(str(b_totals['c'] or 0))

        return (net_adjustment - opening_stock_net - bill_stock_net).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0')


def get_cogs_for_period(from_date=None, to_date=None):
    """Get total COGS (debit only) for a period, excluding closing entries."""
    try:
        cogs_account = ChartOfAccounts.objects.filter(name__icontains='Cost of Goods Sold', status=True).first()
        if not cogs_account: return Decimal('0')

        qs = JournalLine.objects.filter(account=cogs_account, journal__status='posted', status=True, debit__gt=0
        ).exclude(journal__reference__icontains='Closing'
        ).exclude(journal__reference__icontains='Opening Balances')

        if from_date: qs = qs.filter(journal__date__gte=from_date)
        if to_date: qs = qs.filter(journal__date__lte=to_date)

        total = qs.aggregate(total=Sum('debit'))['total'] or 0
        return Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0')


def calculate_inventory_value_matching_pl(item, from_date=None, to_date=None, return_opening=False):
    """
    Calculate inventory closing value using the same formula as P&L:
    Closing = Opening + Purchases + Adjustments - COGS
    
    If from_date is provided, Opening is the state as of (from_date - 1).
    If from_date is None, Opening is the static master data + all time history until to_date.
    """
    try:
        # ── Step 1: Start State ──────────────────────────────────────────────
        if from_date:
            from datetime import timedelta
            if isinstance(from_date, str):
                from datetime import datetime
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            else:
                from_date_obj = from_date
            day_before = from_date_obj - timedelta(days=1)
            start_qty, start_val = calculate_inventory_value_matching_pl(item, from_date=None, to_date=day_before)
        else:
            start_qty, start_val = _get_static_master_data(item, as_of_date=to_date)

        # Mid-period True Opening Journals (against Equity)
        # If we are in a specific period, we must capture opening journals that happened
        # DURING this period and treat them as "Opening Stock" for the report's perspective.
        if from_date and to_date:
            mid_qs = JournalLine.objects.filter(
                account__name__iexact='Stock In Hand',
                journal__date__gte=from_date,
                journal__date__lte=to_date,
                journal__status='posted',
                status=True,
                journal__reference__icontains='OPENING_STOCK'
            ).exclude(journal__reference__icontains='ADJUSTMENT').filter(
                Q(description__icontains=item.name) | 
                Q(journal__reference__icontains=item.name) | 
                Q(journal__narration__icontains=item.name)
            )
            
            mid_totals = mid_qs.aggregate(d=Sum('debit'), c=Sum('credit'))
            mid_val = Decimal(str(mid_totals['d'] or 0)) - Decimal(str(mid_totals['c'] or 0))
            
            if mid_val > 0:
                # Estimate quantity for the mid-period opening
                rate = get_item_cost_rate(item, to_date=to_date)
                mid_qty = (mid_val / rate).quantize(Decimal('0.01')) if rate > 0 else Decimal('0')
                start_qty += mid_qty
                start_val += mid_val
                logger.info(f"Added Mid-period Opening for '{item.name}': {mid_qty} units, {mid_val} value")

        # ── Step 2: Activity ─────────────────────────────────────────────────
        p_qty = get_purchases_qty(item, from_date, to_date)
        p_val = get_purchases_value(item, from_date, to_date)
        s_qty = get_sales_qty(item, from_date, to_date)
        a_val = get_stock_adjustments_value(item, from_date, to_date)
        
        # Estimate adjustment quantity
        a_qty = Decimal('0')
        if a_val != 0:
            rate = get_item_cost_rate(item, to_date=to_date)
            if rate > 0:
                a_qty = (a_val / rate).quantize(Decimal('0.01'))

        # ── Step 3: COGS ─────────────────────────────────────────────────────
        item_cogs = Decimal('0.00')
        if s_qty > 0:
            total_cogs = get_cogs_for_period(from_date, to_date)
            if total_cogs > 0:
                all_s = SalesInvoiceItem.objects.all()
                if from_date: all_s = all_s.filter(sales_inv__date__gte=from_date)
                if to_date: all_s = all_s.filter(sales_inv__date__lte=to_date)
                t_s_qty = Decimal(str(all_s.aggregate(t=Sum('quantity'))['t'] or 0))
                if t_s_qty > 0:
                    item_cogs = (s_qty / t_s_qty) * total_cogs

        # ── Step 4: Final ────────────────────────────────────────────────────
        final_qty = (start_qty + p_qty + a_qty - s_qty).quantize(Decimal('0.01'))
        final_val = (start_val + p_val + a_val - item_cogs).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        final_val = max(final_val, Decimal('0.00'))

        if return_opening:
            return start_qty, start_val
            
        return final_qty, final_val

    except Exception as e:
        logger.error(f"Error in inventory calc for '{item.name}': {str(e)}")
        return Decimal('0'), Decimal('0')


def item_had_activity_by(item, cutoff_date):
    """Check if item had any activity (purchase, sale, journal) on/before cutoff."""
    try:
        if not cutoff_date: return True
        if BillItem.objects.filter(product=item, bill__date__lte=cutoff_date).exists(): return True
        if SalesInvoiceItem.objects.filter(product=item, sales_inv__date__lte=cutoff_date).exists(): return True
        if JournalLine.objects.filter(description__icontains=item.name, journal__date__lte=cutoff_date, journal__status='posted').exists(): return True
        if JournalLine.objects.filter(journal__reference__icontains=f'OPENING_STOCK_{item.name}', journal__date__lte=cutoff_date, journal__status='posted').exists(): return True
        return False
    except Exception:
        return True