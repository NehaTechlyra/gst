from user.utils import has_permission

# Define permissions aliases
_SALES_ALIASES = ['Sales']  # Main sales module for all access
_ITEMS_ALIASES = ['Masters Items', 'Sales Items', 'Items']  # Individual items access
_CUSTOMER_ALIASES = ['Masters Customer', 'Sales Customer', 'Customers']  # Individual customer access
_QUOTATION_ALIASES = ['Sales Quotation', 'Quotations']  # Individual quotation access
_INVOICE_ALIASES = ['Sales Invoice', 'Invoices']  # Individual invoice access
_ORDER_ALIASES = ['Sales Order', 'Orders']  # Individual sales order access
_PAYMENTS_RECEIVED_ALIASES = ['Sales Payments Received', 'Payments Received']  # Individual payments received access
_DELIVERY_ALIASES = ['Sales Delivery', 'Sales Delivery Note']  # Individual delivery access
_RETURN_ALIASES = ['Sales Return', 'Returns']  # Individual returns access
_PERFORMA_INVOICE_ALIASES = ['Sales Performa Invoice', 'Performa Invoice', 'Performa Invoices']  # Individual performa invoice access
_EWAY_BILL_ALIASES = ['Sales Eway Bill', 'E-Way Bills']  # Individual e-way bill access
_DASHBOARD_ALIASES = ['Sales Dashboard']  # Individual sales dashboard access
# Combined aliases for checking overall sales access
_ALL_SALES_ALIASES = _SALES_ALIASES + _ITEMS_ALIASES + _CUSTOMER_ALIASES + _QUOTATION_ALIASES + _INVOICE_ALIASES + _EWAY_BILL_ALIASES


def _any_alias_has_perm(user, aliases, perm='View'):
    """Return True if user has `perm` on any module name in `aliases`."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    # Superusers always have access
    if getattr(user, 'is_superuser', False):
        return True
        
    # Regular users need explicit permissions
    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            # ignore and continue to next alias
            continue
    return False


def check_sales_access(user, perm='View'):
    """Check if user has full sales access."""
    return _any_alias_has_perm(user, _SALES_ALIASES, perm=perm)


def check_sales_module_access(user):
    """Check if user has access to any sales feature."""
    return check_sales_access(user, 'View') or any(
        _any_alias_has_perm(user, aliases, 'View') 
        for aliases in [_ITEMS_ALIASES, _CUSTOMER_ALIASES, _QUOTATION_ALIASES, _EWAY_BILL_ALIASES]
    )


def check_items_access(user, perm='View'):
    """Check if user has access to items.

    NOTE: A global 'Sales' permission grants only 'View' access across the module.
    Create/Edit/Delete must be granted per-submodule (Items) to avoid blanket privileges.
    """
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _ITEMS_ALIASES, perm=perm)


def check_customers_access(user, perm='View'):
    """Check if user has access to customer management."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _CUSTOMER_ALIASES, perm=perm)


def check_quotations_access(user, perm='View'):
    """Check if user has access to quotations."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _QUOTATION_ALIASES, perm=perm)


# Convenience helpers for common permission checks used by views/templates
def can_view_items(user):
    return check_items_access(user, 'View')


def can_create_items(user):
    return check_items_access(user, 'Create')


def can_edit_items(user):
    return check_items_access(user, 'Edit')


def can_delete_items(user):
    return check_items_access(user, 'Delete')


def can_view_customers(user):
    return check_customers_access(user, 'View')


def can_create_customers(user):
    return check_customers_access(user, 'Create')


def can_edit_customers(user):
    return check_customers_access(user, 'Edit')


def can_delete_customers(user):
    return check_customers_access(user, 'Delete')


def can_view_quotations(user):
    return check_quotations_access(user, 'View')


def can_create_quotations(user):
    return check_quotations_access(user, 'Create')


def can_edit_quotations(user):
    return check_quotations_access(user, 'Edit')


def can_delete_quotations(user):
    return check_quotations_access(user, 'Delete')


def check_invoices_access(user, perm='View'):
    """Check if user has access to invoices."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _INVOICE_ALIASES, perm=perm)


def check_orders_access(user, perm='View'):
    """Check if user has access to sales orders."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _ORDER_ALIASES, perm=perm)


def check_payments_received_access(user, perm='View'):
    """Check if user has access to payments received."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _PAYMENTS_RECEIVED_ALIASES, perm=perm)


def check_delivery_access(user, perm='View'):
    """Check if user has access to sales delivery."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _DELIVERY_ALIASES, perm=perm)


def can_view_invoices(user):
    return check_invoices_access(user, 'View')


def can_create_invoices(user):
    return check_invoices_access(user, 'Create')


def can_edit_invoices(user):
    return check_invoices_access(user, 'Edit')


def can_delete_invoices(user):
    return check_invoices_access(user, 'Delete')


def can_view_orders(user):
    return check_orders_access(user, 'View')


def can_create_orders(user):
    return check_orders_access(user, 'Create')


def can_edit_orders(user):
    return check_orders_access(user, 'Edit')


def can_delete_orders(user):
    return check_orders_access(user, 'Delete')


def can_view_payments_received(user):
    return check_payments_received_access(user, 'View')


def can_create_payments_received(user):
    return check_payments_received_access(user, 'Create')


def can_edit_payments_received(user):
    return check_payments_received_access(user, 'Edit')


def can_delete_payments_received(user):
    return check_payments_received_access(user, 'Delete')


def can_view_delivery(user):
    return check_delivery_access(user, 'View')


def can_create_delivery(user):
    return check_delivery_access(user, 'Create')


def can_edit_delivery(user):
    return check_delivery_access(user, 'Edit')


def can_delete_delivery(user):
    return check_delivery_access(user, 'Delete')



def check_returns_access(user, perm='View'):
    """Check if user has access to sales returns."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _RETURN_ALIASES, perm=perm)


def can_view_returns(user):
    return check_returns_access(user, 'View')


def can_create_returns(user):
    return check_returns_access(user, 'Create')


def can_edit_returns(user):
    return check_returns_access(user, 'Edit')


def can_delete_returns(user):
    return check_returns_access(user, 'Delete')


def check_performa_invoice_access(user, perm='View'):
    """Check if user has access to sales performa invoices."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _PERFORMA_INVOICE_ALIASES, perm=perm)


def can_view_performa_invoice(user):
    return check_performa_invoice_access(user, 'View')


def can_create_performa_invoice(user):
    return check_performa_invoice_access(user, 'Create')


def can_edit_performa_invoice(user):
    return check_performa_invoice_access(user, 'Edit')


def can_delete_performa_invoice(user):
    return check_performa_invoice_access(user, 'Delete')

def check_sales_dashboard_access(user, perm='View'):
    """Check if user has access to sales dashboard."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _DASHBOARD_ALIASES, perm=perm)


def can_view_sales_dashboard(user):
    return check_sales_dashboard_access(user, 'View')


def check_eway_bill_access(user, perm='View'):
    """Check if user has access to sales e-way bills."""
    # Strict: require explicit submodule permission for all actions
    return _any_alias_has_perm(user, _EWAY_BILL_ALIASES, perm=perm)


def can_view_eway_bill(user):
    return check_eway_bill_access(user, 'View')


def can_create_eway_bill(user):
    return check_eway_bill_access(user, 'Create')


def can_edit_eway_bill(user):
    return check_eway_bill_access(user, 'Edit')


def can_delete_eway_bill(user):
    return check_eway_bill_access(user, 'Delete')
