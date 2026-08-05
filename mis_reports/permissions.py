"""Permission helpers for the MIS Reports module."""

from user.utils import has_permission, is_app_admin_user, is_app_role_admin


_DASHBOARD_ALIASES = ['MIS Dashboard']
_SALES_ALIASES = ['MIS Sales Report']
_PURCHASE_ALIASES = ['MIS Purchase Report']
_INVENTORY_ALIASES = ['MIS Inventory Report']
_FINANCE_ALIASES = ['MIS Finance Report']
_CRM_ALIASES = ['MIS CRM Report']
_HR_ALIASES = ['MIS HR Report']
_EXPENSE_ALIASES = ['MIS Expense Report']
_EXPORT_ALIASES = ['MIS Export']


def _any_alias_has_perm(user, aliases, perm='View'):
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if (
        getattr(user, 'is_superuser', False)
        or getattr(user, 'is_staff', False)
        or is_app_admin_user(user)
        or is_app_role_admin(user)
    ):
        return True

    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            continue
    return False


def check_dashboard_access(user, perm='View'):
    return _any_alias_has_perm(user, _DASHBOARD_ALIASES, perm=perm)


def check_sales_access(user, perm='View'):
    return _any_alias_has_perm(user, _SALES_ALIASES, perm=perm)


def check_purchase_access(user, perm='View'):
    return _any_alias_has_perm(user, _PURCHASE_ALIASES, perm=perm)


def check_inventory_access(user, perm='View'):
    return _any_alias_has_perm(user, _INVENTORY_ALIASES, perm=perm)


def check_finance_access(user, perm='View'):
    return _any_alias_has_perm(user, _FINANCE_ALIASES, perm=perm)


def check_crm_access(user, perm='View'):
    return _any_alias_has_perm(user, _CRM_ALIASES, perm=perm)


def check_hr_access(user, perm='View'):
    return _any_alias_has_perm(user, _HR_ALIASES, perm=perm)


def check_expense_access(user, perm='View'):
    return _any_alias_has_perm(user, _EXPENSE_ALIASES, perm=perm)


def check_export_access(user, perm='View'):
    return _any_alias_has_perm(user, _EXPORT_ALIASES, perm=perm)


def can_view_dashboard(user):
    return check_dashboard_access(user, 'View')


def can_view_sales(user):
    return check_sales_access(user, 'View')


def can_view_purchase(user):
    return check_purchase_access(user, 'View')


def can_view_inventory(user):
    return check_inventory_access(user, 'View')


def can_view_finance(user):
    return check_finance_access(user, 'View')


def can_view_crm(user):
    return check_crm_access(user, 'View')


def can_view_hr(user):
    return check_hr_access(user, 'View')


def can_view_expense(user):
    return check_expense_access(user, 'View')


def can_export(user):
    return check_export_access(user, 'View')

