"""
Period Locking Validators & Enforcement
Checks if a date falls within a locked period and prevents edits accordingly
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from .models import FiscalYear, PeriodLockExemption


class PeriodLockEnforcer:
    """Handles period lock validation and enforcement"""

    @staticmethod
    def is_period_locked(date_obj, user=None, db='default', transaction_type=None):
        """
        Check if a date falls within a locked fiscal year
        Args:
            date_obj: Date to check
            user: User object (to check exemptions)
            db: Database name to query (default: 'default')
            transaction_type: optional lock category
        Returns: (is_locked: bool, fiscal_year: FiscalYear or None, is_exempted: bool)
        """
        if not date_obj:
            return False, None, False

        # Find fiscal year for this date
        fiscal_year = FiscalYear.objects.using(db).filter(
            start_date__lte=date_obj,
            end_date__gte=date_obj
        ).first()

        if not fiscal_year:
            return False, None, False

        # Check if period is locked or specific transaction type is locked
        if fiscal_year.is_locked:
            locked = True
        elif transaction_type:
            transaction_map = {
                'item': 'lock_items',
                'stock': 'lock_stock',
                'invoice': 'lock_invoices',
                'bill': 'lock_bills',
                'payment': 'lock_payments',
                'journal': 'lock_journals',
                'expense': 'lock_expenses',
                'sales_return': 'lock_sales_return',
                'purchase_return': 'lock_purchase_return',
                'sales_delivery': 'lock_sales_delivery',
                'purchase_delivery': 'lock_purchase_delivery',
            }
            field_name = transaction_map.get(transaction_type.lower())
            locked = bool(field_name and getattr(fiscal_year, field_name, False))
        else:
            locked = False

        if not locked:
            return False, fiscal_year, False

        # Check if user is exempted
        is_exempted = False
        if user and getattr(user, 'is_authenticated', False):
            is_exempted = PeriodLockExemption.objects.using(db).filter(
                fiscal_year=fiscal_year,
                user=user
            ).exists()

        return True, fiscal_year, is_exempted

    @staticmethod
    def check_can_edit(date_obj, user=None, db='default', transaction_type=None):
        """
        Enforce period locking - Raise exception if period is locked and user not exempted
        Args:
            date_obj: Date to check
            user: User object
            db: Database name to query (default: 'default')
            transaction_type: optional lock category
        """
        is_locked, fiscal_year, is_exempted = PeriodLockEnforcer.is_period_locked(
            date_obj, user, db=db, transaction_type=transaction_type
        )

        if is_locked and not is_exempted:
            category_msg = f" ({transaction_type})" if transaction_type else ''
            locked_fields = []
            if fiscal_year.is_locked:
                locked_fields.append('all')
            locked_fields.extend(fiscal_year.locked_categories)

            locked_by = fiscal_year.locked_by.username if fiscal_year.locked_by else 'Admin'
            lock_date = fiscal_year.lock_date.strftime('%d %b %Y, %I:%M %p') if fiscal_year.lock_date else 'N/A'
            locked_areas = ', '.join(sorted(set(locked_fields)))

            html_msg = (
                "❌ Period Locked: The fiscal year is locked for editing" +
                "<br><br>" +
                "<i class='bi bi-lock-fill'></i> <strong>Locked by:</strong> " + str(locked_by) + "<br>" +
                "<i class='bi bi-calendar'></i> <strong>Lock Date:</strong> " + str(lock_date) + "<br>" +
                "<i class='bi bi-info-circle'></i> <strong>Locked areas:</strong> " + str(locked_areas) +
                "<br><br>Contact your administrator to unlock this period if needed."
            )
            raise PermissionDenied(html_msg)

        return True

    @staticmethod
    def get_lock_message(date_obj, db='default'):
        """Get user-friendly lock message for a date"""
        is_locked, fiscal_year, _ = PeriodLockEnforcer.is_period_locked(date_obj, db=db)

        if is_locked:
            return (
                f"🔒 Period Locked: {fiscal_year.name} "
                f"({fiscal_year.start_date.strftime('%d %b %Y')} - "
                f"{fiscal_year.end_date.strftime('%d %b %Y')})"
            )

        if fiscal_year:
            return f"🔓 Open: {fiscal_year.name}"

        return "⚠️ No fiscal year defined for this date"

    @staticmethod
    def get_locked_periods(db='default'):
        """Get all currently locked periods"""
        return FiscalYear.objects.using(db).filter(is_locked=True).order_by('-start_date')

    @staticmethod
    def get_active_fiscal_year(db='default'):
        """Get the currently active fiscal year (if any)"""
        today = timezone.now().date()
        return FiscalYear.objects.using(db).filter(
            start_date__lte=today,
            end_date__gte=today,
            status='active'
        ).first()


def validate_item_edit_date(item_instance, user=None):
    """Validate that item opening stock date is not in locked period"""
    if hasattr(item_instance, 'stocks'):
        # Check opening stock dates for all related stocks
        for stock in item_instance.stocks.all():
            if stock.opening_stock and hasattr(stock, 'created_at'):
                try:
                    PeriodLockEnforcer.check_can_edit(stock.created_at.date(), user)
                except PermissionDenied as e:
                    raise ValidationError(
                        f"Cannot edit item opening stock: {str(e)}"
                    )


def validate_stock_edit_date(stock_instance, user=None):
    """Validate that stock operations are not in locked period"""
    if stock_instance.created_at:
        try:
            PeriodLockEnforcer.check_can_edit(stock_instance.created_at.date(), user)
        except PermissionDenied as e:
            raise ValidationError(
                f"Cannot edit stock: {str(e)}"
            )


def validate_journal_entry_date(journal_entry_instance, user=None):
    """Validate that journal entry date is not in locked period"""
    if journal_entry_instance.date:
        try:
            PeriodLockEnforcer.check_can_edit(journal_entry_instance.date, user)
        except PermissionDenied as e:
            raise ValidationError(
                f"Cannot create/edit journal entry: {str(e)}"
            )


def validate_transaction_date(date_obj, transaction_type="transaction", user=None):
    """
    Generic validation for any transaction date
    transaction_type: 'bill', 'invoice', 'purchase', 'journal', etc.
    """
    try:
        PeriodLockEnforcer.check_can_edit(date_obj, user)
    except PermissionDenied as e:
        raise ValidationError(
            f"❌ Cannot create {transaction_type}: {str(e)}"
        )
