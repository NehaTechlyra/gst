"""
Fiscal Year Closing Utilities

Handles the year-end closing process:
1. Transfer P&L (Income & Expenses) to Retained Earnings
2. Create opening balances for next fiscal year
3. Lock previous year from edits
4. Generate audit trail

KEY DESIGN RULES (READ BEFORE MODIFYING):
==========================================
- Expense accounts are closed ONLY when their debit balance > 0 (real expenses).
- Contra-expense accounts (e.g. Stock Adjustment) have CREDIT balances and are
  NEVER included in the closing journal — they are balance sheet / inventory
  contra accounts and must remain untouched.
- NEVER use abs(balance) for expense closing decisions. Always check the raw
  signed balance so credit-balance expense accounts are correctly skipped.
- The closing journal should only ever contain:
      Dr  Income accounts   (to zero them out)
      Cr  Expense accounts  (ONLY those with positive debit balances)
      Cr  Retained Earnings (net profit) OR Dr Retained Earnings (net loss)
- get_fiscal_year_totals() and create_closing_journal_entry() MUST agree on
  which accounts are included; they both use the same positive-debit-only rule.
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Q, F

from chart_of_accounts.models import ChartOfAccounts
from journal.models import JournalEntry, JournalLine
from .models import FiscalYear, FiscalYearClosing


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _signed_balance(account, lines_qs):
    """
    Return the signed ledger balance for *account* given a pre-filtered
    JournalLine queryset.

    Convention (mirrors reports.py get_account_balance):
        Assets  (type '1' / ''):  Debit − Credit   (positive = debit balance)
        Expense (type '4'):       Debit − Credit   (positive = debit balance)
        Income  (type '3'):       Credit − Debit   (positive = credit balance)
        Liab.   (type '2'):       Credit − Debit
        Equity  (type '5'):       Credit − Debit
    """
    totals = lines_qs.filter(account=account).aggregate(
        td=Sum('debit'), tc=Sum('credit')
    )
    td = Decimal(str(totals['td'] or 0))
    tc = Decimal(str(totals['tc'] or 0))

    if account.type in ('1', '4', ''):
        return td - tc
    else:
        return tc - td


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_account_by_name(name, db='default'):
    """Get a chart of accounts entry by name (case-insensitive)."""
    return ChartOfAccounts.objects.using(db).filter(
        name__iexact=name, status=True
    ).first()


def get_fiscal_year_totals(fiscal_year, db='default'):
    """
    Calculate total income, expenses, and net profit/loss for a fiscal year.

    RULES:
    - Income  (type '3'): include all accounts with credit balance > 0.
    - Expense (type '4'): include ONLY accounts with DEBIT balance > 0.
      Accounts whose net position is a CREDIT (e.g. Stock Adjustment, purchase
      returns, rebates) are contra-expenses and are intentionally excluded.
      Using abs() here would be wrong — it would pull in contra accounts.

    Returns:
        dict: {
            'total_income':    Decimal,
            'total_expenses':  Decimal,
            'net_profit_loss': Decimal,
        }
    """
    base_qs = JournalLine.objects.using(db).filter(
        journal__date__gte=fiscal_year.start_date,
        journal__date__lte=fiscal_year.end_date,
        journal__status='posted',
        status=True,
    ).select_related('account', 'journal')

    total_income = Decimal('0')
    total_expenses = Decimal('0')

    # Collect unique accounts touched in this period
    account_ids = base_qs.values_list('account_id', flat=True).distinct()
    accounts = ChartOfAccounts.objects.using(db).filter(id__in=account_ids)

    for account in accounts:
        balance = _signed_balance(account, base_qs)

        if account.type == '3':          # Income — credit-normal
            if balance > 0:
                total_income += balance

        elif account.type == '4':        # Expense — debit-normal
            # ✅ CRITICAL: Only include genuine expenses (positive debit balance).
            # Contra-expense accounts (e.g. Stock Adjustment) have credit balances
            # (balance < 0 here) and MUST be skipped.
            if balance > 0:
                total_expenses += balance

    net_profit_loss = total_income - total_expenses

    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit_loss': net_profit_loss,
    }


def get_account_balance_at_date(account, fiscal_year, db='default',
                                exclude_opening_entries=False):
    """
    Calculate the balance of an account as of the end of a fiscal year.
    (exclude_opening_entries kept for API compatibility — not used.)
    """
    lines = JournalLine.objects.using(db).filter(
        account=account,
        journal__date__gte=fiscal_year.start_date,
        journal__date__lte=fiscal_year.end_date,
        journal__status='posted',
        status=True,
    )

    totals = lines.aggregate(td=Sum('debit'), tc=Sum('credit'))
    td = Decimal(str(totals['td'] or 0))
    tc = Decimal(str(totals['tc'] or 0))

    if account.type in ('', '1', '4'):
        return td - tc
    else:
        return tc - td


def get_balances_for_balance_sheet_accounts(fiscal_year, db='default'):
    """
    Get balances for all balance sheet accounts (Assets, Liabilities, Equity).
    These are carried forward to the next year.

    Excludes the parent Equity header account (it is a roll-up, not a posting
    account; its balance is represented by its children).

    ✅ CRITICAL FIX:
    - Include ALL balance sheet accounts, not just those with activity in the FY.
      Contra-asset accounts (e.g., Stock Adjustment) may have zero activity in
      the current FY but carry a balance from previous years that MUST be forwarded.
    - Use abs(balance) > Decimal('0.005') to properly include negative balances
      (contra-assets, deferred items, etc.) with rounding tolerance.

    Returns:
        dict: {account_id: Decimal balance}
    """
    # Collect ALL balance sheet accounts (types '1', '2', '5') that are active.
    # This ensures contra-asset accounts without current-year activity are included.
    all_accounts = ChartOfAccounts.objects.using(db).filter(
        type__in=('1', '2', '5'),
        status=True,
    )

    balances = {}

    for account in all_accounts:
        # Skip parent Equity header — profit merges into Opening Balance Equity
        if account.name == 'Equity' and account.type == '5':
            continue

        balance = get_account_balance_at_date(account, fiscal_year, db)

        # DEBUG: Show all balance sheet accounts and their balances
        print(f"DEBUG get_balances_for_balance_sheet_accounts: {account.name}, type={account.type}, balance={balance}")

        # ✅ Include ALL balance sheet accounts with non-zero balance,
        # regardless of sign. Use abs(balance) with rounding tolerance.
        if abs(balance) > Decimal('0.005'):
            balances[account.id] = balance

    return balances


def get_income_and_expense_accounts(fiscal_year, db='default'):
    """
    Return income and expense accounts that should be included in the
    closing journal.

    RULES (must mirror get_fiscal_year_totals):
    - Income  (type '3'): all accounts with credit balance > 0.
    - Expense (type '4'): ONLY accounts with debit balance > 0.
      Contra-expense accounts (credit balance) are excluded.

    Returns:
        dict: {
            'income':   {account_id: Decimal balance},
            'expenses': {account_id: Decimal balance},
        }
    """
    income_accounts = {}
    expense_accounts = {}

    income_qs = ChartOfAccounts.objects.using(db).filter(type='3', status=True)
    expense_qs = ChartOfAccounts.objects.using(db).filter(type='4', status=True)

    for account in income_qs:
        balance = get_account_balance_at_date(account, fiscal_year, db)
        if balance > 0:
            income_accounts[account.id] = balance

    for account in expense_qs:
        balance = get_account_balance_at_date(account, fiscal_year, db)
        # ✅ CRITICAL: skip zero or credit-balance expense accounts
        if balance > 0:
            expense_accounts[account.id] = balance

    return {'income': income_accounts, 'expenses': expense_accounts}


def get_or_create_retained_earnings_account(db='default'):
    """
    Get or auto-create the Retained Earnings account.

    Ensures Retained Earnings sits under the same Equity parent as
    Opening Balance Equity so both appear together on the Balance Sheet.

    Returns:
        ChartOfAccounts: guaranteed to exist.
    """
    # Find the correct Equity parent via Opening Balance Equity's parent
    correct_parent = None
    opening_equity = ChartOfAccounts.objects.using(db).filter(
        name__iexact='Opening Balance Equity', status=True
    ).first()
    if opening_equity and opening_equity.parent:
        correct_parent = opening_equity.parent

    if not correct_parent:
        correct_parent = ChartOfAccounts.objects.using(db).filter(
            name__iexact='Equity', is_header=True, status=True
        ).first()

    if not correct_parent:
        correct_parent = ChartOfAccounts.objects.using(db).create(
            name='Equity', code='5', type='5',
            parent=None, is_header=True, status=True,
            created_by=None, updated_by=None,
        )

    for pattern in ('Retained Earnings', 'Reserves and Surplus'):
        account = ChartOfAccounts.objects.using(db).filter(
            name__icontains=pattern, status=True, type='5'
        ).first()
        if account:
            if account.parent_id != correct_parent.id:
                account.parent = correct_parent
                account.save(using=db)
            return account

    return ChartOfAccounts.objects.using(db).create(
        name='Retained Earnings',
        code='RET-EARNINGS',
        parent=correct_parent,
        type='5',
        is_header=False,
        status=True,
        created_by=None,
        updated_by=None,
    )


def find_retained_earnings_account(db='default'):
    """Deprecated alias — use get_or_create_retained_earnings_account()."""
    return get_or_create_retained_earnings_account(db)


# ---------------------------------------------------------------------------
# Journal entry number helper
# ---------------------------------------------------------------------------

def _next_entry_number(db='default'):
    """Return the next sequential JV-XXXXX entry number."""
    all_entries = JournalEntry.objects.using(db).filter(
        entry_number__startswith='JV-'
    )
    highest = 0
    for entry in all_entries:
        try:
            num = int(entry.entry_number.split('-')[1])
            if num > highest:
                highest = num
        except (IndexError, ValueError):
            pass
    return f'JV-{str(highest + 1).zfill(5)}'


# ---------------------------------------------------------------------------
# Core journal creation
# ---------------------------------------------------------------------------

@transaction.atomic
def create_closing_journal_entry(fiscal_year, request=None, db='default'):
    """
    Create the closing journal entry that transfers P&L to Retained Earnings.

    Closing logic:
        Dr  each income account  (reverse credit balance → zeroes it out)
        Cr  each expense account that has a POSITIVE DEBIT balance
            (reverse debit balance → zeroes it out)
        Cr  Retained Earnings    (net profit)
        — or —
        Dr  Retained Earnings    (net loss)

    ✅ Contra-expense accounts (type '4' but credit balance, e.g. Stock
       Adjustment) are NEVER touched here.  We check `balance > 0` before
       creating any expense closing line.  abs() is intentionally NOT used.

    Returns:
        tuple: (JournalEntry, error_message_or_None)
    """
    try:
        totals = get_fiscal_year_totals(fiscal_year, db)
        pl_accounts = get_income_and_expense_accounts(fiscal_year, db)
        retained_earnings = get_or_create_retained_earnings_account(db)
        user = request.user if request else None

        closing_journal = JournalEntry.objects.using(db).create(
            entry_number=_next_entry_number(db),
            date=fiscal_year.end_date,
            reference=f"Fiscal Year {fiscal_year.name} Closing",
            narration=(
                f"Closing entry for {fiscal_year.name}. "
                f"Income: ₹{totals['total_income']:,.2f}, "
                f"Expenses: ₹{totals['total_expenses']:,.2f}, "
                f"Net: ₹{totals['net_profit_loss']:,.2f}"
            ),
            status='posted',
            created_by=user,
            updated_by=user,
        )

        sequence = 10

        # --- Income accounts: Dr to close (reverse credit balance) ----------
        for account_id, balance in pl_accounts['income'].items():
            account = ChartOfAccounts.objects.using(db).get(id=account_id)
            JournalLine.objects.using(db).create(
                journal=closing_journal,
                account=account,
                description=f"Closing - {account.name}",
                debit=balance,           # balance is already positive (credit-normal)
                credit=Decimal('0'),
                sequence=sequence,
                status=True,
            )
            sequence += 10

        # --- Expense accounts: Cr to close (reverse debit balance) ----------
        # ✅ get_income_and_expense_accounts() already guarantees balance > 0,
        #    but we guard again here to be explicit.
        for account_id, balance in pl_accounts['expenses'].items():
            if balance <= 0:
                # Contra-expense (credit balance) — never close.
                continue
            account = ChartOfAccounts.objects.using(db).get(id=account_id)
            JournalLine.objects.using(db).create(
                journal=closing_journal,
                account=account,
                description=f"Closing - {account.name}",
                debit=Decimal('0'),
                credit=balance,          # balance is positive debit-normal amount
                sequence=sequence,
                status=True,
            )
            sequence += 10

        # --- Net P&L → Retained Earnings ------------------------------------
        net = totals['net_profit_loss']
        if abs(net) > Decimal('0.005'):
            if net > 0:      # Profit → Cr Retained Earnings
                JournalLine.objects.using(db).create(
                    journal=closing_journal,
                    account=retained_earnings,
                    description=f"Net Profit Transfer to {retained_earnings.name}",
                    debit=Decimal('0'),
                    credit=net,
                    sequence=sequence,
                    status=True,
                )
            else:            # Loss → Dr Retained Earnings
                JournalLine.objects.using(db).create(
                    journal=closing_journal,
                    account=retained_earnings,
                    description=f"Net Loss Transfer to {retained_earnings.name}",
                    debit=abs(net),
                    credit=Decimal('0'),
                    sequence=sequence,
                    status=True,
                )

        # Recalculate stored totals
        lines = closing_journal.lines.all()
        closing_journal.total_debit = sum(
            line.debit or Decimal('0') for line in lines
        )
        closing_journal.total_credit = sum(
            line.credit or Decimal('0') for line in lines
        )
        closing_journal.save(using=db)

        return closing_journal, None

    except Exception as e:
        return None, str(e)


@transaction.atomic
def create_opening_balances_journal(fiscal_year, next_fiscal_year,
                                    profit_transfer=None, request=None, db='default'):
    """
    Create opening balance journal entry for the next fiscal year.
    Carries forward all balance sheet account balances.

    Returns:
        tuple: (JournalEntry or None, error_message or None)
    """
    try:
        balances = get_balances_for_balance_sheet_accounts(fiscal_year, db)

        if profit_transfer is None:
            totals = get_fiscal_year_totals(fiscal_year, db)
            profit_transfer = totals['net_profit_loss']
        elif isinstance(profit_transfer, (int, float)):
            profit_transfer = Decimal(str(profit_transfer))

        retained_earnings = get_or_create_retained_earnings_account(db)

        if profit_transfer != 0:
            balances[retained_earnings.id] = profit_transfer

        # Remove parent Equity header from opening balances
        equity_parent = ChartOfAccounts.objects.using(db).filter(
            name__iexact='Equity', type='5', status=True
        ).first()
        if equity_parent and equity_parent.id in balances:
            del balances[equity_parent.id]

        if not balances:
            return None, "No opening balances to transfer"

        user = request.user if request else None

        opening_journal = JournalEntry.objects.using(db).create(
            entry_number=_next_entry_number(db),
            date=next_fiscal_year.start_date,
            reference=f"Opening Balances for {next_fiscal_year.name}",
            narration=(
                f"Opening balance transfer from {fiscal_year.name}. "
                f"Includes profit: ₹{profit_transfer:,.2f}"
            ),
            status='posted',
            created_by=user,
            updated_by=user,
        )

        sequence = 10

        for account_id, balance in balances.items():
            account = ChartOfAccounts.objects.using(db).get(id=account_id)
            account_type = account.type or (account.parent.type if account.parent else '')

            if account_type in ('1', ''):      # Asset — positive = debit
                debit  = balance if balance >= 0 else Decimal('0')
                credit = abs(balance) if balance < 0 else Decimal('0')
            elif account_type in ('2', '5'):   # Liability / Equity — positive = credit
                debit  = abs(balance) if balance < 0 else Decimal('0')
                credit = balance if balance >= 0 else Decimal('0')
            else:
                debit  = abs(balance) if balance < 0 else Decimal('0')
                credit = balance if balance >= 0 else Decimal('0')

            if debit > 0 or credit > 0:
                JournalLine.objects.using(db).create(
                    journal=opening_journal,
                    account=account,
                    description=f"Opening Balance - {account.name}",
                    debit=debit,
                    credit=credit,
                    sequence=sequence,
                    status=True,
                )
                sequence += 10

        lines = opening_journal.lines.all()
        opening_journal.total_debit = sum(
            line.debit or Decimal('0') for line in lines
        )
        opening_journal.total_credit = sum(
            line.credit or Decimal('0') for line in lines
        )
        opening_journal.save(using=db)

        return opening_journal, None

    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------------------
# Bad closing journal reversal (DATABASE CLEANUP)
# ---------------------------------------------------------------------------

@transaction.atomic
def reverse_bad_closing_journal(fiscal_year, request=None, db='default'):
    """
    One-shot cleanup: reverse any closing journal that incorrectly posted
    contra-expense accounts (e.g. Stock Adjustment) during fiscal year closing.

    A "bad" closing journal is identified as:
        - reference contains "{fiscal_year.name} Closing"
        - contains a credit line against an account whose type='4' AND whose
          net balance in that journal is a CREDIT (i.e. a contra-expense was
          incorrectly closed).

    The reversal is a mirror-image journal entry (same lines, debits/credits
    swapped) posted on fiscal_year.end_date.

    After calling this function you should re-run execute_fiscal_year_closing()
    to post the correct closing journal.

    Returns:
        tuple: (reversal_journal or None, error_message or None)
    """
    try:
        user = request.user if request else None

        bad_journals = JournalEntry.objects.using(db).filter(
            reference__icontains=f"{fiscal_year.name} Closing",
            status='posted',
        )

        if not bad_journals.exists():
            return None, (
                f"No closing journal found for {fiscal_year.name}. "
                "Nothing to reverse."
            )

        reversal_entries = []

        for bad_journal in bad_journals:
            lines = bad_journal.lines.filter(status=True)

            # Detect if this journal contains an incorrectly closed
            # contra-expense (credit on a type='4' account)
            has_bad_line = lines.filter(
                account__type='4',
                credit__gt=0,
            ).exists()

            if not has_bad_line:
                continue  # This journal looks correct — skip

            reversal = JournalEntry.objects.using(db).create(
                entry_number=_next_entry_number(db),
                date=fiscal_year.end_date,
                reference=f"REVERSAL — {bad_journal.reference}",
                narration=(
                    f"Reversal of incorrect closing journal #{bad_journal.entry_number} "
                    f"for {fiscal_year.name}. Contra-expense accounts were incorrectly "
                    f"closed. This entry restores them."
                ),
                status='posted',
                created_by=user,
                updated_by=user,
            )

            sequence = 10
            for line in lines:
                JournalLine.objects.using(db).create(
                    journal=reversal,
                    account=line.account,
                    description=f"Reversal - {line.description or line.account.name}",
                    debit=line.credit or Decimal('0'),    # swap
                    credit=line.debit or Decimal('0'),    # swap
                    sequence=sequence,
                    status=True,
                )
                sequence += 10

            reversal_lines = reversal.lines.all()
            reversal.total_debit = sum(
                l.debit or Decimal('0') for l in reversal_lines
            )
            reversal.total_credit = sum(
                l.credit or Decimal('0') for l in reversal_lines
            )
            reversal.save(using=db)
            reversal_entries.append(reversal)

        if not reversal_entries:
            return None, (
                "Closing journal(s) found but none contained incorrectly closed "
                "contra-expense accounts. No reversal needed."
            )

        return reversal_entries, None

    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

def _assert_not_already_closed(fiscal_year, db='default'):
    """
    Raise ValidationError if a completed closing record already exists for
    this fiscal year, preventing double-closing.
    """
    already_closed = FiscalYearClosing.objects.using(db).filter(
        fiscal_year=fiscal_year,
        status='completed',
    ).exists()

    if already_closed:
        raise ValidationError(
            f"Fiscal year '{fiscal_year.name}' has already been closed. "
            "To re-close after a reversal, delete or void the existing "
            "FiscalYearClosing record first."
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

@transaction.atomic
def execute_fiscal_year_closing(fiscal_year, next_fiscal_year,
                                request=None, db='default'):
    """
    Execute the complete fiscal year closing process.

    Steps:
    1. Guard: reject if already closed (idempotency).
    2. Create closing journal entry (P&L → Retained Earnings).
       — Contra-expense accounts are intentionally skipped.
    3. Create opening balances for next year.
    4. Lock current fiscal year; unlock next fiscal year.
    5. Create FiscalYearClosing audit record.

    Args:
        fiscal_year:      FiscalYear to close.
        next_fiscal_year: Next FiscalYear (required for opening balances).
        request:          HTTP request (for user context).
        db:               Database alias.

    Returns:
        tuple: (success: bool, message: str, closing_record or None)
    """
    user = request.user if request else None

    # ✅ Step 1 — Idempotency guard
    try:
        _assert_not_already_closed(fiscal_year, db)
    except ValidationError as e:
        return False, str(e), None

    try:
        # Step 2 — Calculate totals
        totals = get_fiscal_year_totals(fiscal_year, db)

        # Step 3 — Create closing journal
        closing_journal, error = create_closing_journal_entry(
            fiscal_year, request, db
        )
        if error:
            return False, f"Failed to create closing entry: {error}", None

        # Step 4 — Create opening balances (use pre-calculated profit so it
        # is not affected by the closing entry that was just posted)
        opening_journal, error = create_opening_balances_journal(
            fiscal_year, next_fiscal_year,
            profit_transfer=totals['net_profit_loss'],
            request=request,
            db=db,
        )
        if error:
            return False, f"Failed to create opening balances: {error}", None

        # Step 5 — Lock / unlock fiscal years
        fiscal_year.lock(user=user, categories=['all'])
        fiscal_year.status = 'closed'
        fiscal_year.save(using=db)

        if next_fiscal_year:
            next_fiscal_year.status = 'active'
            next_fiscal_year.is_locked = False
            next_fiscal_year.save(using=db)

        # Step 6 — Audit record
        closing_record = FiscalYearClosing.objects.using(db).create(
            fiscal_year=fiscal_year,
            status='completed',
            closing_journal_id=closing_journal.id if closing_journal else None,
            opening_journal_id=opening_journal.id if opening_journal else None,
            total_income=totals['total_income'],
            total_expenses=totals['total_expenses'],
            net_profit_loss=totals['net_profit_loss'],
            initiated_by=user,
            completed_by=user,
            completed_at=timezone.now(),
            notes=(
                f"Successfully closed {fiscal_year.name}. "
                f"Income: ₹{totals['total_income']:,.2f}, "
                f"Expenses: ₹{totals['total_expenses']:,.2f}, "
                f"Net P&L: ₹{totals['net_profit_loss']:,.2f}"
            ),
        )

        return (
            True,
            f"✅ Fiscal year {fiscal_year.name} closed successfully",
            closing_record,
        )

    except Exception as e:
        return False, f"❌ Error during fiscal year closing: {str(e)}", None