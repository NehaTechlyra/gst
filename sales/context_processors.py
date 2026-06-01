from .permissions import (
    check_sales_access, check_items_access,
    check_customers_access, check_quotations_access,
    check_invoices_access, check_orders_access, check_payments_received_access,
    check_delivery_access, check_returns_access,
    check_eway_bill_access,
)

def sales_permissions(request):
    """Context processor that adds Sales-specific permissions to the template context."""
    user = getattr(request, 'user', None)
    
    if not user or not getattr(user, 'is_authenticated', False):
        return {}
        
    # Superusers have all permissions
    if getattr(user, 'is_superuser', False):
        perms = {
            'can_view_sales': True,
            'can_create_sales': True,
            'can_edit_sales': True,
            'can_delete_sales': True,
            'can_view_items': True,
            'can_create_items': True,
            'can_edit_items': True,
            'can_delete_items': True,
            'can_view_customers': True,
            'can_create_customers': True,
            'can_edit_customers': True,
            'can_delete_customers': True,
            'can_view_quotations': True,
            'can_create_quotations': True,
            'can_edit_quotations': True,
            'can_delete_quotations': True,
            'can_view_invoices': True,
            'can_create_invoices': True,
            'can_edit_invoices': True,
            'can_delete_invoices': True,
            'can_view_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,
            'can_delete_orders': True,
            'can_view_payments_received': True,
            'can_create_payments_received': True,
            'can_edit_payments_received': True,
            'can_delete_payments_received': True,
            'can_view_delivery': True,
            'can_create_delivery': True,
            'can_edit_delivery': True,
            'can_delete_delivery': True,
            'can_view_returns': True,
            'can_create_returns': True,
            'can_edit_returns': True,
            'can_delete_returns': True,
            'can_view_eway_bill': True,
            'can_create_eway_bill': True,
            'can_edit_eway_bill': True,
            'can_delete_eway_bill': True,
        }
        return perms

    # For regular users, check both sales-wide and individual permissions
    perms = {}
    
    # Check sales access (gives access to everything)
    perms['can_view_sales'] = check_sales_access(user, 'View')
    if perms['can_view_sales']:
        perms.update({
            'can_create_sales': check_sales_access(user, 'Create'),
            'can_edit_sales': check_sales_access(user, 'Edit'),
            'can_delete_sales': check_sales_access(user, 'Delete'),
        })
        
    # Check individual section permissions
    # Items
    perms['can_view_items'] = check_items_access(user, 'View')
    if perms['can_view_items']:
        perms['can_create_items'] = check_items_access(user, 'Create')
        perms['can_edit_items'] = check_items_access(user, 'Edit')
        perms['can_delete_items'] = check_items_access(user, 'Delete')
        
    # Customers
    perms['can_view_customers'] = check_customers_access(user, 'View')
    if perms['can_view_customers']:
        perms['can_create_customers'] = check_customers_access(user, 'Create')
        perms['can_edit_customers'] = check_customers_access(user, 'Edit')
        perms['can_delete_customers'] = check_customers_access(user, 'Delete')
        
    # Quotations
    perms['can_view_quotations'] = check_quotations_access(user, 'View')
    if perms['can_view_quotations']:
        perms['can_create_quotations'] = check_quotations_access(user, 'Create')
        perms['can_edit_quotations'] = check_quotations_access(user, 'Edit')
        perms['can_delete_quotations'] = check_quotations_access(user, 'Delete')

    # Invoices
    perms['can_view_invoices'] = check_invoices_access(user, 'View')
    if perms['can_view_invoices']:
        perms['can_create_invoices'] = check_invoices_access(user, 'Create')
        perms['can_edit_invoices'] = check_invoices_access(user, 'Edit')
        perms['can_delete_invoices'] = check_invoices_access(user, 'Delete')

    # Orders
    perms['can_view_orders'] = check_orders_access(user, 'View')
    if perms['can_view_orders']:
        perms['can_create_orders'] = check_orders_access(user, 'Create')
        perms['can_edit_orders'] = check_orders_access(user, 'Edit')
        perms['can_delete_orders'] = check_orders_access(user, 'Delete')

    # Payments Received
    perms['can_view_payments_received'] = check_payments_received_access(user, 'View')
    if perms['can_view_payments_received']:
        perms['can_create_payments_received'] = check_payments_received_access(user, 'Create')
        perms['can_edit_payments_received'] = check_payments_received_access(user, 'Edit')
        perms['can_delete_payments_received'] = check_payments_received_access(user, 'Delete')

    # Sales Delivery
    perms['can_view_delivery'] = check_delivery_access(user, 'View')
    if perms['can_view_delivery']:
        perms['can_create_delivery'] = check_delivery_access(user, 'Create')
        perms['can_edit_delivery'] = check_delivery_access(user, 'Edit')
        perms['can_delete_delivery'] = check_delivery_access(user, 'Delete')

    # Sales Returns
    perms['can_view_returns'] = check_returns_access(user, 'View')
    if perms['can_view_returns']:
        perms['can_create_returns'] = check_returns_access(user, 'Create')
        perms['can_edit_returns'] = check_returns_access(user, 'Edit')
        perms['can_delete_returns'] = check_returns_access(user, 'Delete')

    # E-Way Bills
    perms['can_view_eway_bill'] = check_eway_bill_access(user, 'View')
    if perms['can_view_eway_bill']:
        perms['can_create_eway_bill'] = check_eway_bill_access(user, 'Create')
        perms['can_edit_eway_bill'] = check_eway_bill_access(user, 'Edit')
        perms['can_delete_eway_bill'] = check_eway_bill_access(user, 'Delete')

    return perms
