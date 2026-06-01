SYSTEM_MODULES = [
    {
        'id': 1,
        'name': 'User Management',
        'code': 'USER_MGMT',
        'apps': ['user', 'Employee'],
        'icon': 'bi-people',
        'is_core': True,
        'description': 'Manage users, roles, and permissions'
    },
    {
        'id': 2,
        'name': 'Reports & Analytics',
        'code': 'REPORTS',
        'apps': ['chart_of_accounts', 'journal'],
        'icon': 'bi-graph-up',
        'is_core': False,
        'description': 'Generate reports and view analytics'
    },
    {
        'id': 3,
        'name': 'Inventory System',
        'code': 'INVENTORY',
        'apps': ['Items', 'warehouse', 'stock', 'unit', 'category', 'type'],
        'icon': 'bi-box-seam',
        'is_core': False,
        'description': 'Manage inventory and stock'
    },
    {
        'id': 4,
        'name': 'Sales & Purchase',
        'code': 'SALES_PURCHASE',
        'apps': ['sales', 'Purchase', 'customer', 'brand', 'category', 'type','pricelist'],
        'icon': 'bi-cart',
        'is_core': False,
        'description': 'Sales and purchasing workflows'
    },
    {
        'id': 5,
        'name': 'HR Management',
        'code': 'HR',
        'apps': ['HR', 'department', 'designation', 'leaves', 'allowances'],
        'icon': 'bi-person-badge',
        'is_core': False,
        'description': 'Human resource management'
    },
    {
        'id': 6,
        'name': 'Finance',
        'code': 'FINANCE',
        'apps': ['bank', 'expenses', 'Tax', 'PayTerms'],
        'icon': 'bi-currency-rupee',
        'is_core': False,
        'description': 'Financial operations'
    },
    {
        'id': 7,
        'name': 'Email & SMS',
        'code': 'COMMUNICATION',
        'apps': ['email_config', 'sms_config', 'email_templates', 'sms_templates'],
        'icon': 'bi-envelope',
        'is_core': False,
        'description': 'Email and SMS notifications'
    },
    {
        'id': 8,
        'name': 'System Settings',
        'code': 'SYSTEM',
        'apps': ['system_settings', 'company'],
        'icon': 'bi-gear',
        'is_core': True,
        'description': 'Core system configuration'
    },
]

def get_module_by_code(code):
    """Get module by code"""
    for module in SYSTEM_MODULES:
        if module['code'] == code:
            return module
    return None

def get_all_modules():
    """Get all modules"""
    return SYSTEM_MODULES
