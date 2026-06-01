"""
Period Locking Enforcement Validators
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These validators enforce period locking rules across the ERP system.
They prevent edits to locked accounting periods.

Usage:
    from system_settings.period_validators import check_period_locked
    
    check_period_locked(date, user)  # Raises PeriodLockedError if locked
"""

from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import FiscalYear, PeriodLockExemption


class PeriodLockedError(ValidationError):
    """Raised when trying to edit a locked accounting period"""
    pass


def get_fiscal_year_for_date(check_date):
    """
    Get the fiscal year containing the given date.
    
    Args:
        check_date: date object to check
    
    Returns:
        FiscalYear object or None
    """
    if not isinstance(check_date, date):
        return None
    
    return FiscalYear.objects.filter(
        start_date__lte=check_date,
        end_date__gte=check_date
    ).first()


def is_period_locked(check_date, transaction_type=None):
    """
    Check if a date falls within a locked accounting period.
    
    Args:
        check_date: date object to check
        transaction_type: optional lock category
    
    Returns:
        bool: True if period is locked (global or type-specific), False otherwise
    """
    fiscal_year = get_fiscal_year_for_date(check_date)
    if not fiscal_year:
        return False

    if fiscal_year.is_locked:
        return True

    if transaction_type:
        mapping = {
            'item': 'lock_items',
            'stock': 'lock_stock',
            'invoice': 'lock_invoices',
            'bill': 'lock_bills',
            'payment': 'lock_payments',
            'journal': 'lock_journals',
            'expense': 'lock_expenses',
        }
        field = mapping.get(transaction_type.lower())
        if field:
            return getattr(fiscal_year, field, False)

    return False


def is_user_exempted(user, check_date):
    """
    Check if a user has exemption from period locking for a given date.
    Superusers are always exempted.
    
    Args:
        user: User object
        check_date: date object to check
    
    Returns:
        bool: True if user is exempted, False otherwise
    """
    # Superusers always bypass period locking
    if user and user.is_superuser:
        return True
    
    # Check explicit exemption
    fiscal_year = get_fiscal_year_for_date(check_date)
    if not fiscal_year:
        return False
    
    return PeriodLockExemption.objects.filter(
        fiscal_year=fiscal_year,
        user=user
    ).exists()


def check_period_locked(check_date, user=None, transaction_type=None):
    """
    Check if a period is locked and user is not exempted.
    Raises PeriodLockedError if period is locked.
    
    Args:
        check_date: date object to check
        user: User object (optional, for exemption checking)
        transaction_type: optional lock category for fine-grained control
    
    Raises:
        PeriodLockedError: If period is locked and user is not exempted
    """
    fiscal_year = get_fiscal_year_for_date(check_date)

    if not fiscal_year:
        return  # No fiscal year defined for this date, allow editing

    if not is_period_locked(check_date, transaction_type=transaction_type):
        return  # Period is not locked for this type, allow editing

    # Period is locked - check if user is exempted
    if user and is_user_exempted(user, check_date):
        return  # User is exempted, allow editing

    # Period is locked and user is not exempted - BLOCK EDIT
    category_msg = f" ({transaction_type})" if transaction_type else ''
    locked_fields = []
    if fiscal_year.is_locked:
        locked_fields.append('all')
    locked_fields.extend(fiscal_year.locked_categories)

    raise PeriodLockedError(
        f"🔒 The accounting period ({fiscal_year.name}: {fiscal_year.start_date.strftime('%d %b %Y')} to {fiscal_year.end_date.strftime('%d %b %Y')}) is LOCKED{category_msg}. "
        f"Locked when: {', '.join(sorted(set(locked_fields)))}. "
        f"You cannot edit this transaction. Please contact your administrator.",
        code='period_locked'
    )


def check_multiple_periods_locked(dates, user=None):
    """
    Check if multiple dates span across locked periods.
    
    Args:
        dates: List of date objects to check
        user: User object (optional)
    
    Returns:
        dict: {
            'locked_periods': [FiscalYear objects],
            'all_locked': bool
        }
    """
    locked_periods = set()
    
    for check_date in dates:
        fiscal_year = get_fiscal_year_for_date(check_date)
        if fiscal_year and fiscal_year.is_locked:
            if not (user and is_user_exempted(user, check_date)):
                locked_periods.add(fiscal_year.id)
    
    return {
        'locked_periods': list(locked_periods),
        'has_locked_dates': len(locked_periods) > 0
    }


def get_period_lock_message(check_date, fiscal_year=None):
    """
    Get a user-friendly message about period lock status.
    
    Args:
        check_date: date object
        fiscal_year: FiscalYear object (optional, fetched if not provided)
    
    Returns:
        str: Lock status message
    """
    if not fiscal_year:
        fiscal_year = get_fiscal_year_for_date(check_date)
    
    if not fiscal_year:
        return f"No fiscal year defined for {check_date.strftime('%d %b %Y')}"
    
    if fiscal_year.is_locked:
        return (
            f"🔒 Period Locked: {fiscal_year.name} "
            f"({fiscal_year.start_date.strftime('%d %b %Y')} - {fiscal_year.end_date.strftime('%d %b %Y')}) "
            f"is LOCKED. All edits are BLOCKED."
        )
    else:
        return (
            f"🔓 Period Open: {fiscal_year.name} "
            f"({fiscal_year.start_date.strftime('%d %b %Y')} - {fiscal_year.end_date.strftime('%d %b %Y')}) "
            f"is OPEN. Editing is allowed."
        )


def validate_opening_stock_edit(item, date_to_edit, user=None):
    """
    Specialized validator for opening stock edits.
    Opening stock locks to the fiscal year start date.
    
    Args:
        item: Item object
        date_to_edit: date object (typically opening stock date)
        user: User object (optional)
    
    Raises:
        PeriodLockedError: If the period containing the date is locked
    
    Example:
        validate_opening_stock_edit(item, item.opening_stock_date, request.user)
    """
    check_period_locked(date_to_edit, user)


def validate_journal_entry_edit(entry_date, user=None):
    """
    Specialized validator for journal entry edits.
    
    Args:
        entry_date: date of journal entry
        user: User object (optional)
    
    Raises:
        PeriodLockedError: If the period is locked
    """
    check_period_locked(entry_date, user)


def validate_bill_edit(bill_date, user=None):
    """
    Specialized validator for bill/invoice edits.
    
    Args:
        bill_date: date of bill
        user: User object (optional)
    
    Raises:
        PeriodLockedError: If the period is locked
    """
    check_period_locked(bill_date, user)


def validate_stock_transaction_edit(transaction_date, warehouse=None, item=None, user=None):
    """
    Specialized validator for stock transactions.
    
    Args:
        transaction_date: date of stock transaction
        warehouse: Warehouse object (optional, for logging)
        item: Item object (optional, for logging)
        user: User object (optional)
    
    Raises:
        PeriodLockedError: If the period is locked
    """
    check_period_locked(transaction_date, user)


def get_editable_fiscal_years(user=None):
    """
    Get list of fiscal years the user can edit (unlocked or exempted).
    
    Args:
        user: User object
    
    Returns:
        QuerySet: FiscalYear objects user can edit
    """
    if not user:
        return FiscalYear.objects.filter(is_locked=False)
    
    if user.is_superuser:
        return FiscalYear.objects.all()  # Superusers can edit all
    
    # Regular users can edit unlocked periods + exempted periods
    unlocked_ids = FiscalYear.objects.filter(is_locked=False).values_list('id', flat=True)
    exempted_ids = PeriodLockExemption.objects.filter(
        user=user
    ).values_list('fiscal_year_id', flat=True)
    
    return FiscalYear.objects.filter(id__in=list(unlocked_ids) + list(exempted_ids))


def check_fiscal_year_for_new_transaction(user=None):
    """
    Get the current open fiscal year for new transactions.
    
    Args:
        user: User object (optional)
    
    Returns:
        FiscalYear: Current active, open fiscal year or None
    """
    today = timezone.now().date()
    fiscal_year = get_fiscal_year_for_date(today)
    
    if not fiscal_year:
        return None  # No fiscal year for today
    
    if fiscal_year.is_locked:
        # Check if user is exempted
        if user and is_user_exempted(user, today):
            return fiscal_year  # User can still edit
        return None  # Period is locked, cannot edit
    
    return fiscal_year  # Period is open
