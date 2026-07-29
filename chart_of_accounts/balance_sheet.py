"""
Balance Sheet Report Generation
"""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from .models import ChartOfAccounts
from journal.models import JournalLine, JournalEntry
from stock.models import Stock


def get_account_balance(account, as_of_date=None, from_date=None):
    """
    Calculate the balance of an account as of a given date.
    For Assets (type='1'): Debit increases balance (Debit - Credit)
    For Liabilities/Equity ('2', '5'): Credit increases balance (Credit - Debit)
    For Income ('3'): Credit increases balance (Credit - Debit)
    For Expenses ('4'): Debit increases balance (Debit - Credit)
    If from_date is provided, only transactions between from_date and as_of_date are included.

    NOTE: type='' (empty string) is treated as unset — returns 0.0 to avoid
    silent miscalculation from default empty FK values.
    """
    if account.type == '':
        return 0.0

    jl_qs = JournalLine.objects.filter(
        account=account,
        journal__status='posted',
        status=True,
    )

    if from_date:
        jl_qs = jl_qs.filter(journal__date__gte=from_date)

    if as_of_date:
        jl_qs = jl_qs.filter(journal__date__lte=as_of_date)

    totals = jl_qs.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )

    debit_total = Decimal(str(totals['total_debit'] or 0))
    credit_total = Decimal(str(totals['total_credit'] or 0))

    if account.type in ['1', '4']:
        balance = debit_total - credit_total
    else:
        balance = credit_total - debit_total

    return float(balance)


def get_stock_adjustments_balance(to_date=None, from_date=None):
    """
    Calculate net movement in Stock Adjustment accounts.
    Returns positive for Stock Gains (Cr to Adjustment account)
    and negative for Stock Losses (Dr to Adjustment account).
    """
    from django.db.models import Q, Sum
    adj_accounts = ChartOfAccounts.objects.filter(
        Q(name__icontains='Stock Adjustment') |
        Q(name__icontains='Inventory Adjustment'),
        status=True
    )
    total_adj = Decimal('0.00')
    for acc in adj_accounts:
        # We want the net Credit movement (Gains - Losses)
        jl_qs = JournalLine.objects.filter(
            account=acc,
            journal__status='posted',
            status=True,
        ).exclude(journal__reference__icontains='Closing'
        ).exclude(journal__reference__icontains='Opening Balances')

        if from_date:
            jl_qs = jl_qs.filter(journal__date__gte=from_date)
        if to_date:
            jl_qs = jl_qs.filter(journal__date__lte=to_date)

        totals = jl_qs.aggregate(d=Sum('debit'), c=Sum('credit'))
        # Gain = Credit (Stock increase), Loss = Debit (Stock decrease)
        balance = Decimal(str(totals['c'] or 0)) - Decimal(str(totals['d'] or 0))
        total_adj += balance
    
    return total_adj


def get_true_opening_stock_balance(inventory_account, opening_date):
    """
    Get the "True" opening stock balance (Equity portion) as of a date.
    Formula: Total Balance - Cumulative Historical Stock Adjustments.
    """
    # 1. Get the full cumulative balance of Stock In Hand as of opening_date
    total_balance = Decimal(str(get_account_balance(inventory_account, as_of_date=opening_date)))
    
    # 2. Get the cumulative stock adjustments made until that same date
    cumulative_adjustments = get_stock_adjustments_balance(to_date=opening_date)
    
    # 3. True Opening = Total Balance - Total Adjustments
    # If Total = 600 (Lays 200 + Choc 400) and Adjustments = 400, True Opening = 200.
    return total_balance - cumulative_adjustments


def get_true_opening_stock_for_item(item, opening_date=None):
    """
    Calculate the portion of Stock In Hand for this item 
    that was balanced against 'Opening Balance Equity'.
    """
    try:
        from django.db.models import Q, Sum
        stock_account = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand', status=True).first()
        equity_account = ChartOfAccounts.objects.filter(name__icontains='Opening Balance Equity', status=True).first()
        
        if not stock_account or not equity_account:
            return Decimal('0.00')

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




def get_account_balance_excl_closing(account, as_of_date=None, from_date=None):
    """
    =========================================================================
    CHANGE #1 — NEW FUNCTION
    =========================================================================
    Same as get_account_balance() but EXCLUDES fiscal year closing journal
    entries (reference contains 'Closing' or 'Opening Balances').

    WHY THIS IS NEEDED:
    When a fiscal year is closed, two journal entries are created:
      1. Closing entry (Mar 31, 2026): Debits Sales, Credits COGS, Credits Retained Earnings
      2. Opening balance entry (Apr 1, 2026): Debits all asset accounts

    Problem: The closing entry on Mar 31 is dated WITHIN the FY period.
    When we query P&L accounts (Sales, COGS) for FY 2025-26, the closing
    entry is included, making:
        Sales  = 50 (invoice) - 50 (closing debit) = 0   ✗
        COGS   = 40 (real) - 40 (closing credit)   = 0   ✗

    Fix: Exclude journal entries whose reference contains 'Fiscal Year'
    and 'Closing' (the pattern used in fiscal_year_utils.py).
    This gives the true P&L for the period BEFORE the books were closed.

    Used ONLY for income/expense accounts in generate_profit_loss().
    Balance sheet accounts (Stock In Hand, etc.) still use get_account_balance()
    because they need the full picture including closing entries.
    =========================================================================
    """
    if account.type == '':
        return 0.0

    jl_qs = JournalLine.objects.filter(
        account=account,
        journal__status='posted',
        status=True,
    ).exclude(
        # Exclude FY closing entries — these zero out P&L accounts and
        # should not be counted when displaying the period's P&L.
        # Pattern matches: "Fiscal Year FY 2025-26 Closing"
        journal__reference__icontains='Closing'
    ).exclude(
        # Also exclude opening balance entries that carry forward balances
        # Pattern matches: "Opening Balances for FY 2026-27"
        journal__reference__icontains='Opening Balances'
    )

    if from_date:
        jl_qs = jl_qs.filter(journal__date__gte=from_date)

    if as_of_date:
        jl_qs = jl_qs.filter(journal__date__lte=as_of_date)

    totals = jl_qs.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )

    debit_total = Decimal(str(totals['total_debit'] or 0))
    credit_total = Decimal(str(totals['total_credit'] or 0))

    if account.type in ['1', '4']:
        balance = debit_total - credit_total
    else:
        balance = credit_total - debit_total

    return float(balance)


def build_account_hierarchy(parent_account, as_of_date=None, from_date=None, level=0,
                            exclude_closing=False):
    """
    Build hierarchical structure of accounts with balances.

    CHANGE #2: Added exclude_closing parameter.
    When True, uses get_account_balance_excl_closing() instead of
    get_account_balance(). Used for income/expense accounts in P&L
    so that closing journal entries don't zero out the period's P&L.
    """
    children = ChartOfAccounts.objects.filter(
        parent=parent_account,
        status=True
    ).order_by('name')

    hierarchy = []
    parent_balance = 0

    for child in children:
        if exclude_closing:
            balance = get_account_balance_excl_closing(child, as_of_date, from_date)
        else:
            balance = get_account_balance(child, as_of_date, from_date)

        child_data = {
            'id': child.id,
            'code': child.code,
            'name': child.name,
            'balance': balance,
            'level': level,
            'children': [],
            'has_children': ChartOfAccounts.objects.filter(parent=child, status=True).exists()
        }

        if child_data['has_children']:
            child_data['children'], child_balance = build_account_hierarchy(
                child, as_of_date, from_date, level + 1,
                exclude_closing=exclude_closing
            )
            child_data['balance'] += child_balance

        hierarchy.append(child_data)
        parent_balance += child_data['balance']

    return hierarchy, parent_balance


def generate_balance_sheet(as_of_date=None, from_date=None):
    """
    Generate complete hierarchical balance sheet data.
    Balance sheet uses normal get_account_balance (includes closing entries)
    because closing entries ARE part of the balance sheet (they transfer
    profit to Retained Earnings).
    """
    asset_parent = ChartOfAccounts.objects.filter(name__iexact='Asset', status=True).first()
    liability_parent = ChartOfAccounts.objects.filter(name__iexact='Liability', status=True).first()
    equity_parent = ChartOfAccounts.objects.filter(name__iexact='Equity', status=True).first()
    expense_parent = ChartOfAccounts.objects.filter(name__iexact='Expenses', status=True).first()
    income_parent = ChartOfAccounts.objects.filter(name__iexact='Income', status=True).first()

    assets_hierarchy, assets_total = (
        build_account_hierarchy(asset_parent, as_of_date, from_date)
        if asset_parent else ([], 0)
    )
    liabilities_hierarchy, liabilities_total = (
        build_account_hierarchy(liability_parent, as_of_date, from_date)
        if liability_parent else ([], 0)
    )
    equity_hierarchy, equity_hierarchy_total = (
        build_account_hierarchy(equity_parent, as_of_date, from_date)
        if equity_parent else ([], 0)
    )

    equity_total = equity_hierarchy_total
    if equity_parent:
        jl_qs = JournalLine.objects.filter(
            account=equity_parent,
            journal__status='posted',
            status=True,
        )
        if from_date:
            jl_qs = jl_qs.filter(journal__date__gte=from_date)
        if as_of_date:
            jl_qs = jl_qs.filter(journal__date__lte=as_of_date)

        totals = jl_qs.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        parent_debit = Decimal(str(totals['total_debit'] or 0))
        parent_credit = Decimal(str(totals['total_credit'] or 0))
        parent_balance = parent_credit - parent_debit

        if parent_balance != 0:
            equity_total += float(parent_balance)
            parent_equity_entry = {
                'id': equity_parent.id,
                'code': equity_parent.code,
                'name': f"{equity_parent.name} (Profit Transfer)",
                'balance': float(parent_balance),
                'level': 0,
                'children': [],
                'has_children': False
            }
            equity_hierarchy.insert(0, parent_equity_entry)

    expenses_hierarchy, expenses_total = (
        build_account_hierarchy(expense_parent, as_of_date, from_date)
        if expense_parent else ([], 0)
    )
    income_hierarchy, income_total = (
        build_account_hierarchy(income_parent, as_of_date, from_date)
        if income_parent else ([], 0)
    )

    net_profit_loss = income_total - expenses_total
    # Fold unclosed net P&L into Equity as "Retained Earnings" so the sheet
    # balances while the fiscal year is still open (before close_books runs).
    if abs(net_profit_loss) > 0.01:
        equity_total += net_profit_loss
        retained_earnings_entry = {
            'id': 0,
            'code': '',
            'name': 'Retained Earnings',
            'balance': net_profit_loss,
            'level': 0,
            'children': [],
            'has_children': False
        }
        equity_hierarchy.append(retained_earnings_entry)
    total_liabilities_and_equity = liabilities_total + equity_total
    difference = assets_total - total_liabilities_and_equity
    abs_difference = abs(difference)

    return {
        'assets': assets_hierarchy,
        'assets_total': assets_total,
        'liabilities': liabilities_hierarchy,
        'liabilities_total': liabilities_total,
        'equity': equity_hierarchy,
        'equity_total': equity_total,
        'expenses': expenses_hierarchy,
        'expenses_total': expenses_total,
        'income': income_hierarchy,
        'income_total': income_total,
        'net_profit_loss': net_profit_loss,
        'total_liabilities_and_equity': total_liabilities_and_equity,
        'difference': difference,
        'abs_difference': abs_difference,
        'is_balanced': abs_difference < 0.01,
    }


def generate_profit_loss(from_date=None, to_date=None, fy_start_date=None):
    """
    Generate Profit & Loss Statement.

    =========================================================================
    KEY FIX — CLOSING ENTRY EXCLUSION (CHANGE #1, #2, #3)
    =========================================================================

    PROBLEM:
    When a fiscal year is closed, a closing journal entry is posted on the
    last day of the FY (e.g. March 31, 2026) that:
      - DEBITS Sales ₹50    → zeros out Sales
      - CREDITS COGS ₹40    → zeros out COGS
      - CREDITS Retained Earnings ₹10

    This entry is dated WITHIN the FY period, so without the fix:
      - FY 2025-26 Sales = 50 - 50 = 0  ✗
      - FY 2025-26 COGS  = 40 - 40 = 0  ✗

    FIX:
    Use get_account_balance_excl_closing() for income/expense accounts.
    This excludes journal entries whose reference contains 'Closing' or
    'Opening Balances', giving the true pre-closing P&L figures.

    OPENING STOCK:
    Stage 1: Cumulative Stock In Hand balance up to (fy_start - 1 day).
             No from_date limit — captures entries before FY start.
    Stage 2: Formula fallback if Stage 1 = 0:
             Opening = Closing + Real_COGS - Purchases
             Uses _get_real_cogs() which queries ONLY debit entries to avoid
             the closed-FY issue where COGS account balance = 0 after closing.

    CLOSING STOCK:
    Scoped to fy_start_date onward (includes opening balance journal dated
    ON fy_start_date). Uses regular get_account_balance() since stock is a
    balance sheet account that SHOULD include closing/opening entries.

    =========================================================================
    CORRECT EXPECTED VALUES — FY 2025-26:
      Opening Stock : ₹200  (Stage 1 — cumulative as of Mar 31, 2025 = 0,
                              Stage 2 — 200 + 40 - 40 = 200)
      Purchases     : ₹40
      Closing Stock : ₹200  (scoped from Apr 1, 2025 → includes opening
                              balance entry Apr 1, 2025)
      COGS          : ₹40   (excl-closing query gives 40, not 0)
      Sales         : ₹50   (excl-closing query gives 50, not 0)
      Net Profit    : ₹10   ✓

    CORRECT EXPECTED VALUES — FY 2026-27 (active, no transactions yet):
      Opening Stock : ₹200  (Stage 1 — cumulative as of Mar 31, 2026 = 200)
      Purchases     : ₹0
      Closing Stock : ₹200  (scoped from Apr 1, 2026 — opening bal journal)
      COGS          : ₹0
      Sales         : ₹0
      Net Profit    : ₹0    ✓
    =========================================================================
    """
    from Purchase.models import BillItem
    from decimal import Decimal
    import logging
    from datetime import timedelta

    logger = logging.getLogger(__name__)

    income_parent = ChartOfAccounts.objects.filter(name__iexact='Income', status=True).first()
    expense_parent = ChartOfAccounts.objects.filter(name__iexact='Expenses', status=True).first()

    hierarchy_from = from_date or fy_start_date

    # =========================================================================
    # CHANGE #3: Pass exclude_closing=True for income and expense hierarchies.
    # This prevents fiscal year closing entries from zeroing out P&L accounts
    # when viewing a closed fiscal year's P&L.
    # =========================================================================
    income_hierarchy, income_total = (
        build_account_hierarchy(income_parent, to_date, hierarchy_from,
                                exclude_closing=True)    # ← CHANGE #3
        if income_parent else ([], 0)
    )
    expenses_hierarchy, expenses_total = (
        build_account_hierarchy(expense_parent, to_date, hierarchy_from,
                                exclude_closing=True)    # ← CHANGE #3
        if expense_parent else ([], 0)
    )

    # =========================================================================
    # OPENING STOCK — Stage 1: All-time cumulative ledger balance
    # =========================================================================
    # OPENING STOCK — Stage 1: Account Balance
    # =========================================================================
    opening_stock = Decimal('0.00')

    inventory_account_for_opening = ChartOfAccounts.objects.filter(
        name__iexact='Stock In Hand',
        status=True
    ).first()

    if inventory_account_for_opening:
        # Opening date is the day before the period/FY starts
        opening_date = (from_date or fy_start_date or timezone.now().date()) - timedelta(days=1)
        
        if from_date:
            # Sub-period or subsequent year: 
            # Opening Stock is the FULL cumulative balance from the previous day.
            # (In standard accounting, adjustments from last year ARE opening stock this year)
            opening_stock = Decimal(str(get_account_balance(inventory_account_for_opening, opening_date)))
            
            # Capture "True Opening" journals created WITHIN the period
            # These are journals against Opening Balance Equity during the year.
            from django.db.models import Sum
            mid_period_qs = JournalLine.objects.filter(
                account=inventory_account_for_opening,
                journal__date__gte=from_date,
                journal__date__lte=to_date,
                journal__status='posted',
                status=True,
                journal__reference__icontains='OPENING_STOCK'
            ).exclude(journal__reference__icontains='ADJUSTMENT')
            
            mid_period_val = mid_period_qs.aggregate(d=Sum('debit'), c=Sum('credit'))
            mid_period_net = Decimal(str(mid_period_val['d'] or 0)) - Decimal(str(mid_period_val['c'] or 0))
            opening_stock += mid_period_net
            
            logger.info(f"Opening Stock Stage 1 (Carry-forward {opening_date} + Mid-period {mid_period_net}): {opening_stock}")
        else:
            # Full FY Report or System Start:
            # Use "True" Opening logic (Equity Only) to correctly categorize initialization.
            opening_stock = get_true_opening_stock_balance(inventory_account_for_opening, opening_date)
            logger.info(f"Opening Stock Stage 1 (True Opening as of {opening_date}): {opening_stock}")
    
    # If it's a start-of-system report and no true opening journals found, 
    # fall back to Master Data for the first FY.
    if opening_stock == Decimal('0.00') and not from_date:
        # Fallback: Stock master data
        from Items.models import Item
        stock_records = Stock.objects.filter(
            opening_stock__isnull=False,
            item__status=True
        ).exclude(opening_stock=0).select_related('item', 'warehouse')

        if to_date:
            try:
                stock_records = stock_records.filter(created_at__date__lte=to_date)
            except Exception:
                pass

        for stock in stock_records:
            # Check if this item already has journals on or before the opening date
            # that would make master fallback redundant/double-counting.
            opening_date_actual = opening_date + timedelta(days=1) # The start of FY
            
            # 1. Did it have a True Opening (Equity) journal?
            if get_true_opening_stock_for_item(stock.item, opening_date):
                continue
            
            # 2. Does it have an Adjustment journal ON the opening date?
            # (If so, the user intends for it to be an Adjustment, not Opening Stock)
            adj_exists = JournalLine.objects.filter(
                account__name__icontains='Stock Adjustment',
                journal__date=opening_date_actual,
                journal__status='posted',
                status=True
            ).filter(
                Q(description__icontains=stock.item.name) | 
                Q(journal__narration__icontains=stock.item.name)
            ).exists()
            
            if adj_exists:
                logger.info(f"Skipping master fallback for '{stock.item.name}' because opening adjustment exists.")
                continue

            open_qty = Decimal(str(stock.opening_stock)) if stock.opening_stock else Decimal('0.00')
            actual_cost = Decimal('0.00')

            if stock.item.op_rate:
                try:
                    actual_cost = Decimal(str(stock.item.op_rate))
                    if stock.item.taxincld_costprice:
                        total_tax_rate = Decimal('0.00')
                        if stock.item.intra_tax:
                            try:
                                tax_sum = stock.item.intra_tax.taxes.aggregate(Sum('rate'))['rate__sum']
                                if tax_sum:
                                    total_tax_rate = Decimal(str(tax_sum))
                            except Exception as e:
                                logger.warning(f"Failed to get tax rate for '{stock.item.name}': {e}")
                        if total_tax_rate > Decimal('0.00'):
                            multiplier = Decimal('1.00') + (total_tax_rate / Decimal('100.00'))
                            actual_cost = actual_cost / multiplier
                except Exception as e:
                    logger.warning(f"Failed to parse Item.op_rate for '{stock.item.name}': {e}")
                    actual_cost = Decimal('0.00')

            if actual_cost == 0:
                recent_bill_qs = BillItem.objects.filter(product=stock.item)
                if to_date:
                    try:
                        recent_bill_qs = recent_bill_qs.filter(bill__date__lte=to_date)
                    except Exception:
                        pass
                recent_bill_item = recent_bill_qs.order_by('-bill__date', '-id').first()
                if recent_bill_item and recent_bill_item.price:
                    actual_cost = Decimal(str(recent_bill_item.price))
                else:
                    logger.warning(
                        f"Item '{stock.item.name}' has opening stock but NO op_rate and NO bill price"
                    )

            if open_qty > 0 and actual_cost > 0:
                opening_stock += open_qty * actual_cost

    # ===== PURCHASES =====
    purchases_period = Decimal('0.00')
    if from_date and to_date:
        bill_items_period = BillItem.objects.filter(
            bill__date__gte=from_date,
            bill__date__lte=to_date,
            bill__status__in=['Open', 'Closed']
        )
    elif to_date:
        period_start = fy_start_date or to_date
        bill_items_period = BillItem.objects.filter(
            bill__date__gte=period_start,
            bill__date__lte=to_date,
            bill__status__in=['Open', 'Closed']
        )
    else:
        bill_items_period = BillItem.objects.filter(bill__status__in=['Open', 'Closed'])

    for item in bill_items_period:
        purchases_period += Decimal(str(item.quantity or 0)) * Decimal(str(item.price or 0))

    # Cumulative purchases (used in Stage 2 formula)
    purchases_cumulative = Decimal('0.00')
    if to_date:
        if fy_start_date:
            bill_items_cumulative = BillItem.objects.filter(
                bill__date__gte=fy_start_date,
                bill__date__lte=to_date,
                bill__status__in=['Open', 'Closed']
            )
        else:
            bill_items_cumulative = BillItem.objects.filter(
                bill__date__lte=to_date,
                bill__status__in=['Open', 'Closed']
            )
    else:
        bill_items_cumulative = BillItem.objects.filter(bill__status__in=['Open', 'Closed'])

    for item in bill_items_cumulative:
        purchases_cumulative += Decimal(str(item.quantity or 0)) * Decimal(str(item.price or 0))

    # =========================================================================
    # COGS
    # CHANGE #4: Use get_account_balance_excl_closing() for COGS display amount.
    # This gives the real COGS figure for the period, not zeroed out by closing.
    # =========================================================================
    cogs_account = ChartOfAccounts.objects.filter(
        name__iexact='Cost of Goods Sold', status=True
    ).first()
    cogs_amount = Decimal('0.00')
    cogs_cumulative = Decimal('0.00')

    if cogs_account:
        # CHANGE #4: exclude closing entries for the displayed COGS figure
        cogs_balance = get_account_balance_excl_closing(cogs_account, to_date, hierarchy_from)
        cogs_amount = abs(Decimal(str(cogs_balance)))

        # For formula fallback: also get cumulative real COGS (excl closing)
        cogs_balance_cumulative = get_account_balance_excl_closing(cogs_account, to_date, None)
        cogs_cumulative = abs(Decimal(str(cogs_balance_cumulative)))

    # =========================================================================
    # STOCK ADJUSTMENTS
    # NEW: Captures manual entries in Stock Adjustment accounts.
    # =========================================================================
    stock_adjustments = get_stock_adjustments_balance(to_date, from_date)
    logger.info(f"Stock Adjustments for period: {stock_adjustments}")

    # =========================================================================
    # CLOSING STOCK
    # Uses regular get_account_balance() scoped to fy_start_date.
    # Stock In Hand is a balance sheet account — the opening balance journal
    # (dated ON fy_start_date) IS part of the closing stock for this FY.
    # =========================================================================
    closing_stock = Decimal('0.00')

    inventory_account = ChartOfAccounts.objects.filter(
        name__iexact='Stock In Hand',
        status=True
    ).first()

    if inventory_account:
        scope_from = fy_start_date or from_date
        closing_stock_balance = get_account_balance(inventory_account, to_date, scope_from)
        closing_stock = max(Decimal(str(closing_stock_balance)), Decimal('0.00'))
        logger.info(f"Closing Stock (scoped from {scope_from} to {to_date}): {closing_stock}")
    else:
        logger.warning("Stock In Hand account not found; using formula for closing stock")
        closing_stock = opening_stock + purchases_cumulative - cogs_cumulative

    # =========================================================================
    # OPENING STOCK — Stage 2: Formula fallback
    # Formula: Opening = Closing + COGS - Purchases - Adjustments
    # =========================================================================
    if opening_stock == Decimal('0.00') and (
        closing_stock > Decimal('0.00') or cogs_cumulative > Decimal('0.00')
    ):
        derived_opening = closing_stock + cogs_cumulative - purchases_cumulative - stock_adjustments
        if derived_opening > Decimal('0.00'):
            opening_stock = derived_opening
            logger.info(
                f"Opening Stock Stage 2 formula "
                f"(Closing={closing_stock} + COGS={cogs_cumulative} - "
                f"Purchases={purchases_cumulative}): {opening_stock}"
            )

    # =========================================================================
    # SALES — CHANGE #5: Use get_account_balance_excl_closing()
    # Closing entry debits Sales to zero it out — exclude that entry.
    # =========================================================================
    sales_total = Decimal('0.00')
    sales_account = ChartOfAccounts.objects.filter(name__iexact='Sales', status=True).first()
    if sales_account:
        # CHANGE #5: exclude closing entries so Sales shows correctly for closed FYs
        sales_balance = get_account_balance_excl_closing(sales_account, to_date, hierarchy_from)
        sales_total = Decimal(str(sales_balance))

    # ===== NON-OPERATING INCOME =====
    non_operating_income_total = Decimal('0.00')
    for income_account in income_hierarchy:
        if 'Indirect' in income_account.get('name', ''):
            non_operating_income_total += Decimal(str(income_account.get('balance', 0)))

    # ===== GROSS PROFIT =====
    gross_profit = sales_total - cogs_amount

    # ===== OPERATING EXPENSES (Indirect Expenses) =====
    operating_expenses = []
    operating_expenses_total = Decimal('0.00')
    for expense in expenses_hierarchy:
        if 'Indirect' in expense.get('name', ''):
            operating_expenses = expense.get('children', [])
            operating_expenses_total = Decimal(str(expense.get('balance', 0)))

    # ===== NET PROFIT/LOSS =====
    net_profit_loss = gross_profit - operating_expenses_total

    return {
        'opening_stock': float(opening_stock),
        'purchases': float(purchases_period),
        'stock_adjustments': float(stock_adjustments),
        'closing_stock': float(closing_stock),
        'cogs': float(cogs_amount),
        'sales': float(sales_total),
        'gross_profit': float(gross_profit),
        'operating_expenses': operating_expenses,
        'operating_expenses_total': float(operating_expenses_total),
        'non_operating_income': float(non_operating_income_total),
        'net_profit_loss': float(net_profit_loss),
        'income': income_hierarchy,
        'income_total': income_total,
        'expenses': expenses_hierarchy,
        'expenses_total': expenses_total,
    }


def generate_trial_balance(as_of_date=None, from_date=None):
    """
    Generate Trial Balance showing all accounts with their debit/credit balances.
    Trial balance uses regular get_account_balance (includes all entries).
    """
    all_accounts = (
        ChartOfAccounts.objects.filter(status=True)
        .exclude(parent__isnull=True)
        .order_by('name')
    )

    trial_balance = []
    total_debit = 0
    total_credit = 0

    for account in all_accounts:
        balance = get_account_balance(account, as_of_date, from_date=from_date)

        if account.type in ['1', '4']:
            if balance >= 0:
                debit = balance
                credit = 0
            else:
                debit = 0
                credit = abs(balance)
        else:
            if balance >= 0:
                credit = balance
                debit = 0
            else:
                debit = abs(balance)
                credit = 0

        trial_balance.append({
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'type': account.type,
            'debit': debit,
            'credit': credit,
            'balance': balance,
        })

        total_debit += debit
        total_credit += credit

    return {
        'accounts': trial_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'difference': total_debit - total_credit,
        'is_balanced': abs(total_debit - total_credit) < 0.01,
    }


@transaction.atomic
def close_books(as_of_date, company=None):
    """
    Close books for a period using 2-step closing process.
    """
    from journal.models import JournalEntry, JournalLine as JL
    import logging
    logger = logging.getLogger(__name__)

    pl_data = generate_profit_loss(to_date=as_of_date)
    net_result = pl_data['net_profit_loss']

    if abs(net_result) < 0.01:
        return {'status': 'success', 'message': 'No profit/loss to close', 'closing_entries': 0}

    try:
        expense_parent = ChartOfAccounts.objects.filter(name__iexact='Expenses', status=True).first()
        income_parent = ChartOfAccounts.objects.filter(name__iexact='Income', status=True).first()
        pl_account = ChartOfAccounts.objects.filter(name__iexact='Profit & Loss', status=True).first()

        if not pl_account:
            return {'status': 'error', 'message': 'Profit & Loss account not found in Chart of Accounts'}

        closing_entry_1 = JournalEntry.objects.create(
            date=as_of_date,
            description=f'Closing Entry (Step 1) - Close Income & Expenses to P&L as of {as_of_date}',
            status='posted'
        )

        if expense_parent:
            expense_accounts = ChartOfAccounts.objects.filter(parent=expense_parent, status=True)
            for exp_account in expense_accounts:
                exp_balance = get_account_balance(exp_account, as_of_date)
                if abs(exp_balance) > 0.01:
                    JL.objects.create(
                        journal=closing_entry_1,
                        account=exp_account,
                        debit=0,
                        credit=exp_balance,
                        status=True
                    )

        if income_parent:
            income_accounts = ChartOfAccounts.objects.filter(parent=income_parent, status=True)
            for inc_account in income_accounts:
                inc_balance = get_account_balance(inc_account, as_of_date)
                if abs(inc_balance) > 0.01:
                    JL.objects.create(
                        journal=closing_entry_1,
                        account=inc_account,
                        debit=inc_balance,
                        credit=0,
                        status=True
                    )

        if net_result > 0:
            JL.objects.create(journal=closing_entry_1, account=pl_account,
                              debit=net_result, credit=0, status=True)
        else:
            JL.objects.create(journal=closing_entry_1, account=pl_account,
                              debit=0, credit=abs(net_result), status=True)

        equity_parent = ChartOfAccounts.objects.filter(name__iexact='Equity', status=True).first()
        retained_earnings = ChartOfAccounts.objects.filter(
            name__iexact='Retained Earnings', status=True).first()

        if not retained_earnings and equity_parent:
            retained_earnings = ChartOfAccounts.objects.filter(
                parent=equity_parent, status=True).first()

        if not retained_earnings:
            return {'status': 'error', 'message': 'Retained Earnings or Capital account not found'}

        closing_entry_2 = JournalEntry.objects.create(
            date=as_of_date,
            description=f'Closing Entry (Step 2) - Close P&L to Capital as of {as_of_date}',
            status='posted'
        )

        if net_result > 0:
            JL.objects.create(journal=closing_entry_2, account=pl_account,
                              debit=net_result, credit=0, status=True)
            JL.objects.create(journal=closing_entry_2, account=retained_earnings,
                              debit=0, credit=net_result, status=True)
        else:
            JL.objects.create(journal=closing_entry_2, account=pl_account,
                              debit=0, credit=abs(net_result), status=True)
            JL.objects.create(journal=closing_entry_2, account=retained_earnings,
                              debit=abs(net_result), credit=0, status=True)

        return {
            'status': 'success',
            'message': f'Books closed successfully as of {as_of_date}',
            'net_result': net_result,
            'closing_entries': 2,
            'entry_ids': [closing_entry_1.id, closing_entry_2.id]
        }

    except Exception as e:
        logger.exception(f"close_books failed for {as_of_date}: {e}")
        return {'status': 'error', 'message': str(e)}


def _classify_by_hierarchy(account_obj):
    current = account_obj.parent
    depth = 0
    max_depth = 10

    while current and depth < max_depth:
        parent_name_lower = current.name.lower()

        if any(k in parent_name_lower for k in ['current asset', 'accounts receivable', 'debtors', 'stock', 'inventory']):
            return 'current_asset'
        if any(k in parent_name_lower for k in ['current liability', 'accounts payable', 'creditors', 'payable', 'payroll']):
            return 'current_liability'
        if any(k in parent_name_lower for k in ['input tax', 'tax asset', 'gst receivable']):
            return 'current_asset'
        if any(k in parent_name_lower for k in ['output tax', 'tax liability', 'duties and taxes']):
            return 'current_liability'
        if any(k in parent_name_lower for k in ['fixed asset', 'building', 'equipment', 'machinery', 'vehicle', 'furniture', 'property', 'plant']):
            return 'fixed_asset'
        if 'accumulated depreciation' in parent_name_lower:
            return 'depreciation'
        if any(k in parent_name_lower for k in ['investment', 'securities', 'deposits', 'long-term asset']):
            return 'fixed_asset'
        if any(k in parent_name_lower for k in ['loan', 'borrowing', 'overdraft', 'mortgage', 'secured loan', 'unsecured loan']):
            return 'loan'
        if any(k in parent_name_lower for k in ['capital account', 'equity', 'capital', 'opening balance equity', 'shareholders fund', 'reserves', 'surplus']):
            return 'equity'
        if 'depreciation' in parent_name_lower and 'accumulated' not in parent_name_lower:
            return 'depreciation'

        current = current.parent
        depth += 1

    return 'other'


def classify_account(account_name, account_obj=None):
    if not account_obj:
        return 'other'
    if not account_obj.parent:
        return 'other'
    result = _classify_by_hierarchy(account_obj)
    return result if result != 'other' else 'other'


def _is_output_tax_account(account):
    current = account.parent
    depth = 0
    while current and depth < 10:
        pnl = current.name.lower()
        if 'output tax' in pnl or 'duties and taxes' in pnl or ('output' in pnl and 'gst' in pnl):
            return True
        current = current.parent
        depth += 1
    return False


def _is_input_tax_account(account):
    current = account.parent
    depth = 0
    while current and depth < 10:
        pnl = current.name.lower()
        if 'input tax' in pnl or 'tax asset' in pnl or ('input' in pnl and 'gst' in pnl):
            return True
        current = current.parent
        depth += 1
    return False


def generate_cash_flow_statement(from_date=None, to_date=None, fy_start_date=None):
    """
    Generate Cash Flow Statement using the Indirect Method.
    Cash flow uses the corrected P&L net profit (which now excludes closing entries)
    so net_profit_loss will be correct for both open and closed FYs.
    """
    import logging
    logger = logging.getLogger(__name__)
    from datetime import timedelta

    if not from_date and not fy_start_date:
        raise ValueError(
            "generate_cash_flow_statement requires either from_date or fy_start_date."
        )

    opening_date = (from_date - timedelta(days=1)) if from_date else (fy_start_date - timedelta(days=1))
    balance_from_date = fy_start_date or from_date
    period_start = from_date or fy_start_date

    all_accounts = ChartOfAccounts.objects.filter(status=True).select_related('parent')

    def is_cash_account(account):
        account_class = classify_account(account.name, account)
        if account_class in ['loan', 'current_liability', 'fixed_liability']:
            return False
        current = account.parent
        depth = 0
        while current and depth < 10:
            n = current.name.lower().strip()
            if 'loans and advances' in n or 'loans & advances' in n:
                return False
            if n in ['cash', 'cash in hand', 'bank accounts', 'banks', 'bank']:
                return True
            if 'cash' in n and 'hand' in n:
                return True
            if 'bank' in n and 'account' in n:
                return True
            current = current.parent
            depth += 1
        return False

    def get_same_day_opening_transfer_balance(account):
        """
        Fiscal-year opening balance journals are dated on the first day of the
        year. For cash flow, those balances are the opening position, not cash
        movement during the year.
        """
        if not period_start:
            return Decimal('0.00')

        totals = JournalLine.objects.filter(
            account=account,
            journal__date=period_start,
            journal__status='posted',
            journal__reference__icontains='Opening Balances',
            status=True,
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        debit_total = Decimal(str(totals['total_debit'] or 0))
        credit_total = Decimal(str(totals['total_credit'] or 0))

        if account.type in ['1', '4']:
            return debit_total - credit_total
        return credit_total - debit_total

    def is_opening_balance_equity_account(account):
        current = account
        depth = 0
        while current and depth < 10:
            if 'opening balance' in current.name.lower():
                return True
            current = current.parent
            depth += 1
        return False

    def is_retained_earnings_account(account):
        return 'retained earnings' in account.name.lower()

    opening_balances = {}
    closing_balances = {}
    for account in all_accounts:
        opening_balance = Decimal(str(
            get_account_balance(account, as_of_date=opening_date, from_date=balance_from_date)
        ))
        opening_balance += get_same_day_opening_transfer_balance(account)
        opening_balances[account.name] = opening_balance
        closing_balances[account.name] = Decimal(str(
            get_account_balance(account, as_of_date=to_date, from_date=balance_from_date)
        ))

    cash_headers_with_children = set()
    for account in all_accounts:
        if is_cash_account(account) and account.is_header:
            if account.children.filter(status=True, is_header=False).exists():
                cash_headers_with_children.add(account.id)

    opening_cash = Decimal('0.00')
    closing_cash = Decimal('0.00')
    for account in all_accounts:
        if not is_cash_account(account):
            continue
        if account.is_header and account.id in cash_headers_with_children:
            continue
        ob = opening_balances.get(account.name, Decimal('0.00'))
        cb = closing_balances.get(account.name, Decimal('0.00'))
        is_overdraft = False
        cur = account.parent
        d = 0
        while cur and d < 10:
            if 'overdraft' in cur.name.lower():
                is_overdraft = True
                break
            cur = cur.parent
            d += 1
        if is_overdraft:
            opening_cash -= ob
            closing_cash -= cb
        else:
            opening_cash += ob
            closing_cash += cb

    net_change_in_cash = closing_cash - opening_cash

    # generate_profit_loss now correctly excludes closing entries
    pl_data = generate_profit_loss(from_date=from_date, to_date=to_date, fy_start_date=fy_start_date)
    net_profit_loss = Decimal(str(pl_data['net_profit_loss']))
    pl_opening_stock = Decimal(str(pl_data.get('opening_stock', 0)))
    pl_closing_stock = Decimal(str(pl_data.get('closing_stock', 0)))

    depreciation_items = []
    depreciation_total = Decimal('0.00')
    for account in all_accounts:
        if classify_account(account.name, account) == 'depreciation':
            b = Decimal(str(get_account_balance(account, as_of_date=to_date, from_date=from_date)))
            if abs(b) > Decimal('0.01'):
                depreciation_items.append({'name': account.name, 'amount': float(abs(b))})
                depreciation_total += abs(b)

    working_capital_items = []
    receivable_change = Decimal('0.00')
    payable_change = Decimal('0.00')
    inventory_change = pl_closing_stock - pl_opening_stock
    stock_adjustments = Decimal(str(pl_data.get('stock_adjustments', 0)))
    cash_inventory_change = inventory_change - stock_adjustments
    input_tax_total = Decimal('0.00')
    output_tax_total = Decimal('0.00')

    for account in all_accounts:
        if _is_input_tax_account(account):
            o = opening_balances.get(account.name, Decimal('0.00'))
            c = closing_balances.get(account.name, Decimal('0.00'))
            ch = c - o
            input_tax_total += ch
            working_capital_items.append({
                'id': account.id, 'type': 'Input Tax', 'name': account.name,
                'opening_balance': float(o), 'closing_balance': float(c),
                'change': float(ch), 'cash_impact': float(-ch),
                'classification': 'Input Tax accounts (net change)'
            })

    for account in all_accounts:
        if _is_output_tax_account(account):
            o = opening_balances.get(account.name, Decimal('0.00'))
            c = closing_balances.get(account.name, Decimal('0.00'))
            ch = c - o
            output_tax_total += ch
            working_capital_items.append({
                'id': account.id, 'type': 'Output Tax', 'name': account.name,
                'opening_balance': float(o), 'closing_balance': float(c),
                'change': float(ch), 'cash_impact': float(ch),
                'classification': 'Output Tax accounts (net change)'
            })

    inv_acct = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand', status=True).first()
    working_capital_items.append({
        'id': inv_acct.id if inv_acct else 0,
        'type': 'Inventory', 'name': inv_acct.name if inv_acct else 'Stock In Hand',
        'opening_balance': float(pl_opening_stock), 'closing_balance': float(pl_closing_stock),
        'change': float(inventory_change), 'cash_impact': float(-cash_inventory_change),
        'classification': (
            'Inventory movement includes non-cash stock adjustments; cash impact excludes those adjustments'
            if abs(stock_adjustments) > Decimal('0.01')
            else ('Asset increased -> cash tied up in inventory -> less cash'
                  if inventory_change > 0 else 'Asset decreased -> sold from inventory -> more cash')
        ),
    })

    for account in all_accounts:
        is_receivable = False
        cur = account.parent
        d = 0
        while cur and d < 10:
            if any(k in cur.name.lower() for k in ['receivable', 'debtor', 'customer', 'accounts receivable']):
                is_receivable = True
                break
            cur = cur.parent
            d += 1
        if is_receivable and not _is_input_tax_account(account):
            o = opening_balances.get(account.name, Decimal('0.00'))
            c = closing_balances.get(account.name, Decimal('0.00'))
            ch = c - o
            receivable_change += ch
            working_capital_items.append({
                'id': account.id, 'type': 'Receivables', 'name': account.name,
                'opening_balance': float(o), 'closing_balance': float(c),
                'change': float(ch), 'cash_impact': float(-ch),
                'classification': ('Asset increased → cash tied up with customers → less cash'
                                   if ch > 0 else 'Asset decreased → cash collected from customers → more cash')
            })

    for account in all_accounts:
        if classify_account(account.name, account) == 'current_liability' and not _is_output_tax_account(account):
            o = opening_balances.get(account.name, Decimal('0.00'))
            c = closing_balances.get(account.name, Decimal('0.00'))
            ch = c - o
            payable_change += ch
            working_capital_items.append({
                'id': account.id, 'type': 'Payables', 'name': account.name,
                'opening_balance': float(o), 'closing_balance': float(c),
                'change': float(ch), 'cash_impact': float(ch),
                'classification': ('Liability increased → delayed payment to suppliers → more cash'
                                   if ch > 0 else 'Liability decreased → paid off suppliers → less cash')
            })

    operating_cash_flow = (net_profit_loss - cash_inventory_change - receivable_change
                           - input_tax_total + payable_change + output_tax_total + depreciation_total)

    investing_items = []
    investing_cash_flow = Decimal('0.00')
    for account in all_accounts:
        ac = classify_account(account.name, account)
        o = opening_balances.get(account.name, Decimal('0.00'))
        c = closing_balances.get(account.name, Decimal('0.00'))
        ch = c - o
        is_la = False
        cur = account.parent
        d = 0
        while cur and d < 10:
            if 'loans' in cur.name.lower() and 'advances' in cur.name.lower() and 'asset' in cur.name.lower():
                is_la = True
                break
            cur = cur.parent
            d += 1
        if (ac == 'fixed_asset' or is_la) and abs(ch) > Decimal('0.01'):
            ci = ch if is_la else -ch
            investing_cash_flow += ci
            investing_items.append({'id': account.id, 'date': to_date, 'name': account.name,
                                    'adjustment': float(ci), 'type': 'outflow' if ci < 0 else 'inflow'})

    financing_items = []
    financing_cash_flow = Decimal('0.00')
    processed_accounts = set()
    for account in all_accounts:
        if account.name in processed_accounts:
            continue
        if is_opening_balance_equity_account(account) or is_retained_earnings_account(account):
            continue
        ac = classify_account(account.name, account)
        o = opening_balances.get(account.name, Decimal('0.00'))
        c = closing_balances.get(account.name, Decimal('0.00'))
        ch = c - o
        is_borrowing = (ac == 'loan')
        is_capital = (ac == 'equity')
        is_cc = is_capital and ch > 0
        if (is_borrowing or is_cc) and abs(ch) > Decimal('0.01'):
            processed_accounts.add(account.name)
            adj = ch
            if is_cc:
                cur = account.parent
                d = 0
                is_ca = False
                while cur and d < 10:
                    if 'capital' in cur.name.lower():
                        is_ca = True
                        break
                    cur = cur.parent
                    d += 1
                if is_ca:
                    adj = ch - pl_opening_stock
            financing_cash_flow += adj
            financing_items.append({'id': account.id, 'date': to_date, 'name': account.name,
                'adjustment': float(adj), 'type': 'inflow' if adj > 0 else 'outflow'})

    filtered_wc = []
    grouped = {}
    for item in working_capital_items:
        cv = Decimal(str(item['change']))
        civ = Decimal(str(item['cash_impact']))
        it = item['type']
        if abs(cv) < Decimal('0.01'):
            continue
        if it in ['Input Tax', 'Output Tax']:
            if it not in grouped:
                grouped[it] = {'type': it, 'name': f'{it} Accounts (Net)', 'items': [],
                               'total_change': Decimal('0.00'), 'total_cash_impact': Decimal('0.00')}
            grouped[it]['items'].append(item)
            grouped[it]['total_change'] += cv
            grouped[it]['total_cash_impact'] += civ
        else:
            filtered_wc.append(item)

    for gt in ['Input Tax', 'Output Tax']:
        if gt in grouped:
            g = grouped[gt]
            if abs(g['total_change']) > Decimal('0.01'):
                filtered_wc.append({
                    'id': 0, 'type': g['type'], 'name': g['name'],
                    'opening_balance': float(sum(Decimal(str(i['opening_balance'])) for i in g['items'])),
                    'closing_balance': float(sum(Decimal(str(i['closing_balance'])) for i in g['items'])),
                    'change': float(g['total_change']), 'cash_impact': float(g['total_cash_impact']),
                    'classification': f'{gt} accounts (net change)',
                    'sub_items': g['items'], 'is_grouped': True,
                })

    total_activities = operating_cash_flow + investing_cash_flow + financing_cash_flow
    variance = closing_cash - (opening_cash + total_activities)

    return {
        'period': {'from_date': from_date, 'to_date': to_date, 'opening_date': opening_date},
        'operating_activities': {
            'net_profit_loss': float(net_profit_loss),
            'depreciation_items': depreciation_items,
            'depreciation_total': float(depreciation_total),
            'working_capital_items': filtered_wc,
            'working_capital_adjustment': float(-cash_inventory_change - receivable_change - input_tax_total + payable_change + output_tax_total),
            'net_cash_from_operating': float(operating_cash_flow),
        },
        'investing_activities': {'items': investing_items, 'net_cash_from_investing': float(investing_cash_flow)},
        'financing_activities': {'items': financing_items, 'net_cash_from_financing': float(financing_cash_flow)},
        'cash_movement': {
            'opening_cash_balance': float(opening_cash),
            'net_change_in_cash': float(net_change_in_cash),
            'closing_cash_balance': float(closing_cash),
            'expected_closing_cash': float(opening_cash + total_activities),
            'variance': float(variance),
            'is_balanced': abs(variance) < Decimal('0.01'),
        },
    }
