from user.utils import has_permission

# Aliases used in RolePermission.module names
_VENDOR_ALIASES = ['Masters vendor', 'Masters Vendor', 'Vendor', 'vendor']
_PURCHASE_ORDER_ALIASES = ['Purchase Order', 'purchase order', 'Purchase Orders']
_PURCHASE_BILLS_ALIASES = ['Purchase Bills', 'purchase bills', 'Bills']
_PURCHASE_DELIVERY_ALIASES = ['Purchase Delivery', 'purchase delivery']
_PURCHASE_EXPENSES_ALIASES = ['Purchase Expenses', 'purchase expenses']
_PURCHASE_PAYMENTS_ALIASES = ['Purchase Payments Made', 'purchase payments made', 'Payments Made']
_PURCHASE_RETURN_ALIASES = ['Purchase Return', 'purchase return', 'Purchase Returns']
_PURCHASE_DASHBOARD_ALIASES = ['Purchase Dashboard']


def _any_alias_has_perm(user, aliases, perm='View'):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            continue
    return False


# Masters Vendor helpers
def can_view_vendors(user):
    return _any_alias_has_perm(user, _VENDOR_ALIASES, 'View')


def can_create_vendors(user):
    return _any_alias_has_perm(user, _VENDOR_ALIASES, 'Create')


def can_edit_vendors(user):
    return _any_alias_has_perm(user, _VENDOR_ALIASES, 'Edit')


def can_delete_vendors(user):
    return _any_alias_has_perm(user, _VENDOR_ALIASES, 'Delete')


# Purchase Order helpers
def can_view_purchase_orders(user):
    return _any_alias_has_perm(user, _PURCHASE_ORDER_ALIASES, 'View')


def can_create_purchase_orders(user):
    return _any_alias_has_perm(user, _PURCHASE_ORDER_ALIASES, 'Create')


def can_edit_purchase_orders(user):
    return _any_alias_has_perm(user, _PURCHASE_ORDER_ALIASES, 'Edit')


def can_delete_purchase_orders(user):
    return _any_alias_has_perm(user, _PURCHASE_ORDER_ALIASES, 'Delete')


# Purchase Bills helpers
def can_view_purchase_bills(user):
    return _any_alias_has_perm(user, _PURCHASE_BILLS_ALIASES, 'View')


def can_create_purchase_bills(user):
    return _any_alias_has_perm(user, _PURCHASE_BILLS_ALIASES, 'Create')


def can_edit_purchase_bills(user):
    return _any_alias_has_perm(user, _PURCHASE_BILLS_ALIASES, 'Edit')


def can_delete_purchase_bills(user):
    return _any_alias_has_perm(user, _PURCHASE_BILLS_ALIASES, 'Delete')


# Purchase Delivery helpers
def can_view_purchase_delivery(user):
    return _any_alias_has_perm(user, _PURCHASE_DELIVERY_ALIASES, 'View')


def can_create_purchase_delivery(user):
    return _any_alias_has_perm(user, _PURCHASE_DELIVERY_ALIASES, 'Create')


def can_edit_purchase_delivery(user):
    return _any_alias_has_perm(user, _PURCHASE_DELIVERY_ALIASES, 'Edit')


def can_delete_purchase_delivery(user):
    return _any_alias_has_perm(user, _PURCHASE_DELIVERY_ALIASES, 'Delete')


# Purchase Expenses helpers
def can_view_purchase_expenses(user):
    return _any_alias_has_perm(user, _PURCHASE_EXPENSES_ALIASES, 'View')


def can_create_purchase_expenses(user):
    return _any_alias_has_perm(user, _PURCHASE_EXPENSES_ALIASES, 'Create')


def can_edit_purchase_expenses(user):
    return _any_alias_has_perm(user, _PURCHASE_EXPENSES_ALIASES, 'Edit')


def can_delete_purchase_expenses(user):
    return _any_alias_has_perm(user, _PURCHASE_EXPENSES_ALIASES, 'Delete')


# Purchase Payments Made helpers
def can_view_purchase_payments(user):
    return _any_alias_has_perm(user, _PURCHASE_PAYMENTS_ALIASES, 'View')


def can_create_purchase_payments(user):
    return _any_alias_has_perm(user, _PURCHASE_PAYMENTS_ALIASES, 'Create')


def can_edit_purchase_payments(user):
    return _any_alias_has_perm(user, _PURCHASE_PAYMENTS_ALIASES, 'Edit')


def can_delete_purchase_payments(user):
    return _any_alias_has_perm(user, _PURCHASE_PAYMENTS_ALIASES, 'Delete')


# Purchase Return helpers
def can_view_purchase_returns(user):
    return _any_alias_has_perm(user, _PURCHASE_RETURN_ALIASES, 'View')


def can_create_purchase_returns(user):
    return _any_alias_has_perm(user, _PURCHASE_RETURN_ALIASES, 'Create')


def can_edit_purchase_returns(user):
    return _any_alias_has_perm(user, _PURCHASE_RETURN_ALIASES, 'Edit')


def can_delete_purchase_returns(user):
    return _any_alias_has_perm(user, _PURCHASE_RETURN_ALIASES, 'Delete')

def can_view_purchase_dashboard(user):
    return _any_alias_has_perm(user, _PURCHASE_DASHBOARD_ALIASES, 'View')
