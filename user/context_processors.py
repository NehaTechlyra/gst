#by sisira - COMPLETE FINAL FIX: License filtering for all permissions including Masters
from .models import User, RolePermission, Module
import logging
from Lyraerp.utils.license_utils import get_module_category

logger = logging.getLogger(__name__)


def _is_user_management_route(request):
    """Return True if the request path is part of user/role management routes.

    This is used to exempt user-management pages from license-based global
    blocking (so administrators can still manage users/roles when needed).
    Keep the check conservative and only match obvious management fragments.
    """
    try:
        path = (request.path or '').lower()
        # Match common user management endpoints
        fragments = (
            '/user/',
            '/users/',
            'roles',
            'roles/',
            'validate-user-field',
            'debug-visible-modules',
        )
        return any(f in path for f in fragments)
    except Exception:
        return False

# Import permission check functions safely
try:
    from Items.permissions import (
        can_view_items as items_can_view,
        can_create_items as items_can_create,
        can_edit_items as items_can_edit,
        can_delete_items as items_can_delete,
    )
except ImportError:
    items_can_view = lambda u: False
    items_can_create = lambda u: False
    items_can_edit = lambda u: False
    items_can_delete = lambda u: False

try:
    from category.permissions import (
        can_view_categories,
        can_create_categories,
        can_edit_categories,
        can_delete_categories,
    )
except ImportError:
    can_view_categories = lambda u: False
    can_create_categories = lambda u: False
    can_edit_categories = lambda u: False
    can_delete_categories = lambda u: False

try:
    from type.permissions import (
        can_view_types,
        can_create_types,
        can_edit_types,
        can_delete_types,
    )
except ImportError:
    can_view_types = lambda u: False
    can_create_types = lambda u: False
    can_edit_types = lambda u: False
    can_delete_types = lambda u: False

try:
    from sales.permissions import can_view_customers
except ImportError:
    can_view_customers = lambda u: False

try:
    from .permissions import can_view_users, can_view_user_roles
except ImportError:
    can_view_users = lambda u: False
    can_view_user_roles = lambda u: False

try:
    from warehouse.permissions import can_view_warehouse, can_create_warehouse, can_edit_warehouse, can_delete_warehouse
except ImportError:
    can_view_warehouse = lambda u: False
    can_create_warehouse = lambda u: False
    can_edit_warehouse = lambda u: False
    can_delete_warehouse = lambda u: False

try:
    from Purchase.permissions import can_view_vendors, can_create_vendors, can_edit_vendors, can_delete_vendors
except ImportError:
    can_view_vendors = lambda u: False
    can_create_vendors = lambda u: False
    can_edit_vendors = lambda u: False
    can_delete_vendors = lambda u: False

try:
    from Tax.permissions import can_view_taxes, can_create_taxes, can_edit_taxes, can_delete_taxes
except ImportError:
    can_view_taxes = lambda u: False
    can_create_taxes = lambda u: False
    can_edit_taxes = lambda u: False
    can_delete_taxes = lambda u: False

try:
    from stock.permissions import can_view_stock, can_create_stock, can_edit_stock, can_delete_stock
except ImportError:
    can_view_stock = lambda u: False
    can_create_stock = lambda u: False
    can_edit_stock = lambda u: False
    can_delete_stock = lambda u: False

try:
    from PayTerms.permissions import can_view_payterms, can_create_payterms, can_edit_payterms, can_delete_payterms
except ImportError:
    can_view_payterms = lambda u: False
    can_create_payterms = lambda u: False
    can_edit_payterms = lambda u: False
    can_delete_payterms = lambda u: False

try:
    from brand.permissions import can_view_brands, can_create_brands, can_edit_brands, can_delete_brands
except ImportError:
    can_view_brands = lambda u: False
    can_create_brands = lambda u: False
    can_edit_brands = lambda u: False
    can_delete_brands = lambda u: False

try:
    from unit.permissions import can_view_units, can_create_units, can_edit_units, can_delete_units
except ImportError:
    can_view_units = lambda u: False
    can_create_units = lambda u: False
    can_edit_units = lambda u: False
    can_delete_units = lambda u: False

try:
    from bank.permissions import (
        can_view_banking,
        can_create_banking,
        can_edit_banking,
        can_delete_banking,
        can_view_reconciliation,
        can_create_reconciliation,
        can_edit_reconciliation,
        can_delete_reconciliation,
    )
except ImportError:
    can_view_banking = lambda u: False
    can_create_banking = lambda u: False
    can_edit_banking = lambda u: False
    can_delete_banking = lambda u: False
    can_view_reconciliation = lambda u: False
    can_create_reconciliation = lambda u: False
    can_edit_reconciliation = lambda u: False
    can_delete_reconciliation = lambda u: False

try:
    from mis_reports.permissions import (
        can_export as mis_can_export,
        can_view_crm as mis_can_view_crm,
        can_view_dashboard as mis_can_view_dashboard,
        can_view_expense as mis_can_view_expense,
        can_view_finance as mis_can_view_finance,
        can_view_hr as mis_can_view_hr,
        can_view_inventory as mis_can_view_inventory,
        can_view_purchase as mis_can_view_purchase,
        can_view_sales as mis_can_view_sales,
    )
except ImportError:
    mis_can_export = lambda u: False
    mis_can_view_crm = lambda u: False
    mis_can_view_dashboard = lambda u: False
    mis_can_view_expense = lambda u: False
    mis_can_view_finance = lambda u: False
    mis_can_view_hr = lambda u: False
    mis_can_view_inventory = lambda u: False
    mis_can_view_purchase = lambda u: False
    mis_can_view_sales = lambda u: False

def get_license_allowed_modules(request):
    """
    Get list of allowed modules from license
    Based on is_license_expired flag (set by scheduled task at midnight)
    
    Returns:
        None if full license (all modules allowed)
        List of module codes if restricted license
        [] if license expired or no license (no modules allowed)
    """
    try:
        license_info = getattr(request, 'license_info', {})
        is_expired = license_info.get('is_expired', False)
        allowed_modules = license_info.get('allowed_modules', None)

        logger.debug(f"🔑 [LICENSE] License status: is_expired={is_expired}, allowed={allowed_modules}")

        # CRITICAL: Return empty list if license is expired
        if is_expired:
            logger.warning(f"[WARNING] [LICENSE] License expired - returning empty modules list")
            return []

        # Return the allowed modules (None = all modules, [] = no modules)
        return allowed_modules if allowed_modules is not None else None

    except Exception as e:
        logger.error(f"[ERROR] [LICENSE] Error getting allowed modules: {e}")
        return None  # Fail open - allow all modules on error


def permissions_for_request(request):
    """
    COMPLETE FINAL FIX: Context processor with LICENSE-BASED filtering

    This processor:
    1. Checks for valid license first
    2. Loads user permissions from company database
    3. Filters by license key (what modules company paid for)
    4. Returns visible modules and permission flags for templates
    5. NEW: Allows all modules for TRIAL users without license

    Returns:
        dict with:
        - user_permissions: {module_name: {perm_type: bool}} (license-filtered)
        - visible_modules: [module_names with View permission] (license-filtered)
        - can_view_*, can_create_*, etc.: individual permission flags (license-filtered)
        - has_valid_license: bool flag indicating if company has valid license
    """
    user_permissions = {}
    visible_modules = []
    has_valid_license = False
    is_trial = False  # NEW: Track trial status

    try:
        if request.user and request.user.is_authenticated:

            # GET COMPANY DATABASE FROM SESSION
            company_db = request.session.get('company_db', 'default')

            # CHECK LICENSE STATUS FIRST
            license_info = getattr(request, 'license_info', {})
            has_valid_license = license_info.get('has_license', False) and license_info.get('is_valid', False)

            # NEW: Check if company is in trial mode from middleware
            is_trial = license_info.get('trial_active', False)

            logger.debug(f"[TRIAL] Company trial status: {is_trial}")
            logger.debug(f"[LICENSE] User {request.user.username} has valid license: {has_valid_license}, Trial: {is_trial}")

            # For activity history pages, keep role-based sidebar visibility even when
            # license checks are bypassed by middleware exemptions.
            is_activity_history_path = 'activity/new_logs/' in (request.path or '')
            is_license_status_path = any(fragment in (request.path or '') for fragment in (
                'trial-expired',
                'license/restricted',
                'activate-license',
            ))

            # CRITICAL: If no valid license and NOT trial, return empty permissions
            # (except superuser and activity-history pages).
            if (
                not has_valid_license
                and not is_trial
                and not getattr(request.user, 'is_superuser', False)
                and not is_activity_history_path
                and not _is_user_management_route(request)
            ):
                if not is_license_status_path:
                    logger.warning(f"[WARNING] [LICENSE] No valid license and not trial for user {request.user.username} - denying all access")
                return {
                    'user_permissions': {},
                    'visible_modules': [],
                    'has_valid_license': False,
                    # All permission flags set to False
                    'can_view_quotations': False,
                    'can_view_orders': False,
                    'can_view_invoices': False,
                    'can_view_payments_received': False,
                    'can_view_dashboard': False,
                    'can_view_employees': False,
                    'can_view_recruitment': False,
                    'can_view_master': False,
                    'can_view_items': False,
                    'can_view_customers': False,
                    'can_view_users': False,
                    'can_view_user_roles': False,
                    'can_view_warehouse': False,
                    'can_create_warehouse': False,
                    'can_edit_warehouse': False,
                    'can_delete_warehouse': False,
                    'can_view_vendors': False,
                    'can_create_vendors': False,
                    'can_edit_vendors': False,
                    'can_delete_vendors': False,
                    'can_view_taxes': False,
                    'can_create_taxes': False,
                    'can_edit_taxes': False,
                    'can_delete_taxes': False,
                    'can_view_stock': False,
                    'can_create_stock': False,
                    'can_edit_stock': False,
                    'can_delete_stock': False,
                    'can_view_payterms': False,
                    'can_create_payterms': False,
                    'can_edit_payterms': False,
                    'can_delete_payterms': False,
                    'can_view_brands': False,
                    'can_create_brands': False,
                    'can_edit_brands': False,
                    'can_delete_brands': False,
                    'can_view_units': False,
                    'can_create_units': False,
                    'can_edit_units': False,
                    'can_delete_units': False,
                }

            # GET LICENSE-ALLOWED MODULES
            license_allowed_modules = get_license_allowed_modules(request)
            logger.debug(f"[LICENSE] Allowed modules: {license_allowed_modules}")
            logger.debug(f"[SEARCH] [CONTEXT] Loading permissions from database: {company_db} for user: {request.user.username}")

            # ============================================
            # SUPERUSER HANDLING
            # ============================================
            try:
                if getattr(request.user, 'is_superuser', False):
                    visible_modules = list(Module.objects.using(company_db).values_list('name', flat=True))
                    for m in visible_modules:
                        user_permissions.setdefault(m, {})['Full Access'] = True
                        for p in ('View', 'Create', 'Edit', 'Delete'):
                            user_permissions[m].setdefault(p, True)

                    logger.debug(f"[OK] [CONTEXT] Superuser - loaded {len(visible_modules)} modules from {company_db}")

                    # FILTER SUPERUSER BY LICENSE (if license exists and NOT trial)
                    if has_valid_license and not is_trial and license_allowed_modules is not None:
                        logger.debug(f"[SECURE] [LICENSE] Filtering superuser modules by license: {license_allowed_modules}")
                        filtered_visible = []
                        filtered_permissions = {}
                        for module_name in visible_modules:
                            module_category = get_module_category(module_name)
                            if module_category in license_allowed_modules:
                                filtered_visible.append(module_name)
                                filtered_permissions[module_name] = user_permissions[module_name]
                            else:
                                logger.debug(f"[ERROR] [LICENSE] Superuser blocked from '{module_name}' by license")
                        visible_modules = filtered_visible
                        user_permissions = filtered_permissions
                        logger.debug(f"[OK] [LICENSE] Superuser filtered to {len(visible_modules)} modules")
                    elif is_trial:
                        logger.debug(f"[TRIAL] Trial user - showing all {len(visible_modules)} modules")

                    logger.debug(f"📋 [CONTEXT] Final superuser modules: {visible_modules}")

                    # Apply module aliases
                    visible_modules = _apply_module_aliases(visible_modules, user_permissions)

                    # Compute permission flags (now also receives visible_modules)
                    permission_flags = _compute_permission_flags(user_permissions, request.user, visible_modules)

                    return {
                        'user_permissions': user_permissions,
                        'visible_modules': visible_modules,
                        'has_valid_license': True,  # Superuser always has access
                        **permission_flags
                    }

            except Exception as e:
                logger.error(f"[ERROR] [CONTEXT] Error loading superuser permissions: {e}", exc_info=True)

            # ============================================
            # REGULAR USER HANDLING
            # ============================================

            # QUERY COMPANY DATABASE FOR USER
            try:
                app_user = User.objects.using(company_db).filter(
                    usr_name=request.user.username
                ).first()

                if not app_user:
                    app_user = User.objects.using(company_db).filter(
                        usr_mail=request.user.email
                    ).first() if getattr(request.user, 'email', None) else None

                if not app_user:
                    logger.warning(f"[WARNING] [CONTEXT] User {request.user.username} not found in {company_db}")
                else:
                    logger.debug(f"[OK] [CONTEXT] Found user {request.user.username} in {company_db}")

            except Exception as e:
                logger.error(f"[ERROR] [CONTEXT] Error querying user from {company_db}: {e}", exc_info=True)
                app_user = None

            role = getattr(app_user, 'usr_roleid', None) if app_user else None

            if role:
                logger.debug(f"[SEARCH] [CONTEXT] Found role: {role.role_name} (ID: {role.id}) for user {request.user.username}")

                # BUILD PERMISSIONS FROM COMPANY DATABASE
                try:
                    rps = RolePermission.objects.using(company_db).filter(
                        role=role,
                        allowed=1
                    ).select_related('module', 'permission_type')

                    perm_count = rps.count()
                    logger.debug(f"[STATS] [CONTEXT] Found {perm_count} active role permissions in {company_db}")

                    if perm_count == 0:
                        logger.warning(f"[WARNING] [CONTEXT] No active permissions found for role {role.id}")
                        total_perms = RolePermission.objects.using(company_db).filter(role=role).count()
                        if total_perms > 0:
                            logger.warning(f"[WARNING] [CONTEXT] Found {total_perms} permissions but all are disabled (allowed=0)")
                        else:
                            logger.error(f"[ERROR] [CONTEXT] No permissions exist at all for role {role.id}")

                    # BUILD PERMISSION DICT
                    for rp in rps:
                        mname = (rp.module.name or '').strip()
                        pname = (rp.permission_type.name or '').strip()
                        if not mname:
                            continue
                        user_permissions.setdefault(mname, {})[pname] = True
                        if pname == 'Full Access':
                            user_permissions[mname]['View'] = True
                            user_permissions[mname]['Create'] = True
                            user_permissions[mname]['Edit'] = True
                            user_permissions[mname]['Delete'] = True
                            logger.debug(f"[OK] [CONTEXT] Full Access granted for {mname} - auto-enabled View/Create/Edit/Delete")
                        logger.debug(f"[OK] [CONTEXT] Permission: {mname} - {pname}")

                    for m, perms in list(user_permissions.items()):
                        for p in ('View', 'Create', 'Edit', 'Delete', 'Full Access'):
                            perms.setdefault(p, False)

                    visible_modules = [m for m, perms in user_permissions.items() if perms.get('View') or perms.get('Full Access')]

                    logger.debug(f"[OK] [CONTEXT] Visible modules before license filter: {len(visible_modules)} modules")
                    logger.debug(f"[LIST] [CONTEXT] Modules: {visible_modules}")

                    # CRITICAL FIX: Filter BOTH visible_modules AND user_permissions by license (but NOT for trial users)
                    if license_allowed_modules is not None and not is_trial:
                        logger.debug(f"[SECURE] [LICENSE] Filtering modules by license: {license_allowed_modules}")
                        filtered_visible = []
                        filtered_permissions = {}
                        for module_name in visible_modules:
                            module_category = get_module_category(module_name)
                            if module_category in license_allowed_modules:
                                filtered_visible.append(module_name)
                                filtered_permissions[module_name] = user_permissions[module_name]
                            else:
                                logger.debug(f"[ERROR] [LICENSE] Module '{module_name}' (category: {module_category}) blocked by license")
                        visible_modules = filtered_visible
                        user_permissions = filtered_permissions  # KEY FIX
                        logger.debug(f"[OK] [LICENSE] After filtering: {len(visible_modules)} modules visible")
                        logger.debug(f"[OK] [LICENSE] user_permissions also filtered to {len(user_permissions)} modules")
                    elif is_trial:
                        logger.debug(f"[TRIAL] Trial user - NOT filtering modules by license")

                    logger.debug(f"[LIST] [CONTEXT] Final visible modules: {visible_modules}")

                except Exception as e:
                    logger.error(f"[ERROR] [CONTEXT] Error loading role permissions: {e}", exc_info=True)

            else:
                # [FIXED] REMOVED: Trial users should still respect assigned role permissions
                # Do not grant all modules just because company is in trial mode
                # If trial features are needed, handle them at UI level, not permission level
                logger.warning(f"[WARNING] [CONTEXT] No role found for user {request.user.username}")

    except Exception as e:
        logger.error(f"[ERROR] [CONTEXT] Context processor error: {e}", exc_info=True)
        user_permissions = {}
        visible_modules = []

    # APPLY MODULE ALIASES (license-aware)
    license_allowed_modules = get_license_allowed_modules(request) if 'get_license_allowed_modules' in globals() else None
    visible_modules = _apply_module_aliases(visible_modules, user_permissions, license_allowed_modules)
    logger.debug(f"[LIST] [CONTEXT] Final visible modules after aliases: {visible_modules}")

    # [FIXED] REMOVED: Final safeguard trial bypass
    # Trial users should not get automatic full module access
    # Permissions must be enforced consistently regardless of trial status

    # CRITICAL FIX: Compute permission flags from FILTERED user_permissions
    permission_flags = _compute_permission_flags(user_permissions, request.user, visible_modules)

    return {
        'user_permissions': user_permissions,
        'visible_modules': visible_modules,
        'has_valid_license': has_valid_license,
        **permission_flags
    }


def _apply_module_aliases(visible_modules, user_permissions, license_allowed_modules=None):
    """Apply module aliases - only if base modules are visible"""
    try:
        # Helper to check if an alias/category is allowed by license
        def alias_allowed(alias_name):
            if license_allowed_modules is None:
                return True
            try:
                from Lyraerp.utils.license_utils import get_module_category
                return get_module_category(alias_name) in license_allowed_modules
            except Exception:
                return True
        if 'HR' in visible_modules and 'HR Management' not in visible_modules and alias_allowed('HR Management'):
            visible_modules.append('HR Management')

        # Only add HR alias if there is at least one HR submodule with View/Full Access
        hr_submodules = [m for m in visible_modules if m and m.strip().lower().startswith('hr')]
        hr_with_perms = [m for m in hr_submodules if user_permissions.get(m, {}).get('View', False) or user_permissions.get(m, {}).get('Full Access', False)]
        if hr_with_perms and 'HR' not in visible_modules and alias_allowed('HR'):
            visible_modules.append('HR')

        sales_modules = [m for m in visible_modules if m and 'sales' in m.strip().lower()]
        # Require that at least one sales submodule has a View/FullAccess permission
        sales_with_perms = [m for m in sales_modules if user_permissions.get(m, {}).get('View', False) or user_permissions.get(m, {}).get('Full Access', False)]
        if sales_with_perms:
            if 'Sales' not in visible_modules and alias_allowed('Sales'):
                visible_modules.append('Sales')
                logger.debug("[OK] [ALIAS] Added 'Sales' parent alias")
            if 'Sales Management' not in visible_modules and alias_allowed('Sales Management'):
                visible_modules.append('Sales Management')
            for sales_mod in sales_with_perms:
                perms = user_permissions.get(sales_mod, {})
                for alias in ['Sales', 'Sales Management']:
                    if alias not in user_permissions:
                        user_permissions[alias] = perms.copy()

        crm_submodules = [m for m in visible_modules if m and m.strip().lower().startswith('crm')]
        if crm_submodules and 'CRM' not in visible_modules and alias_allowed('CRM'):
            visible_modules.append('CRM')
            logger.debug("[OK] [ALIAS] Added 'CRM' parent alias")

        purchase_keywords = ['purchase', 'bill']
        purchase_submodules = [m for m in visible_modules if m and any(
            kw in m.strip().lower() for kw in purchase_keywords
        ) and 'eway' not in m.strip().lower()]
        
        if purchase_submodules and 'Purchase' not in visible_modules and alias_allowed('Purchase'):
            visible_modules.append('Purchase')
            logger.debug(f"[OK] [ALIAS] Added 'Purchase' parent alias (found: {purchase_submodules})")

        # Do not auto-grant Purchase modules from Masters Vendor.
        # Purchase access must come from explicit Purchase role permissions.

        account_modules = [m for m in visible_modules if m and (
            'account' in m.strip().lower() or
            'chart' in m.strip().lower() or
            'journal' in m.strip().lower()
        )]
        if account_modules:
            if 'Accounts' not in visible_modules and alias_allowed('Accounts'):
                visible_modules.append('Accounts')
            for m in account_modules:
                if 'chart' in m.strip().lower() and 'Chart of Accounts' not in visible_modules:
                    if alias_allowed('Chart of Accounts'):
                        visible_modules.append('Chart of Accounts')
                if 'journal' in m.strip().lower() and 'Journal' not in visible_modules:
                    if alias_allowed('Journal'):
                        visible_modules.append('Journal')

        reports_submodules = [m for m in visible_modules if m and m.strip().startswith('Reports ')]
        if reports_submodules and 'Reports' not in visible_modules and alias_allowed('Reports'):
            visible_modules.append('Reports')

        master_keywords = ['Items', 'Customer', 'Vendor', 'Warehouse', 'Stock', 'Tax', 'User', 'Role', 'Brand', 'Unit', 'Payment Terms']
        master_modules = [m for m in visible_modules if m and any(kw.lower() in m.lower() for kw in master_keywords)]
        # Only add Masters alias when at least one master submodule has View/FullAccess
        master_with_perms = [m for m in master_modules if user_permissions.get(m, {}).get('View', False) or user_permissions.get(m, {}).get('Full Access', False)]
        if master_with_perms and 'Masters' not in visible_modules and alias_allowed('Masters'):
            visible_modules.append('Masters')
            logger.debug(f"[OK] [ALIAS] Added 'Masters' parent alias (found: {master_with_perms})")

        system_keywords = ['prefix', 'setting', 'configuration', 'system']

        # Only consider a module as a 'system' or 'admin' module if the user
        # actually has View or Full Access for it. This prevents parent aliases
        # like 'System settings' from appearing when a user only has unrelated
        # aliases (for example, a CRM alias) without explicit system perms.
        def _module_has_view(m):
            perms = user_permissions.get(m, {})
            return perms.get('View', False) or perms.get('Full Access', False)

        has_system_modules = [
            m for m in visible_modules
            if m and any(kw in m.strip().lower() for kw in system_keywords) and _module_has_view(m)
        ]

        has_admin_modules = [
            m for m in visible_modules
            if m and m.strip().lower() in ['masters', 'admin', 'configuration'] and _module_has_view(m)
        ]

        if (has_system_modules or has_admin_modules) and 'System settings' not in visible_modules and alias_allowed('System settings'):
            visible_modules.append('System settings')
            logger.debug("[OK] [ALIAS] Added 'System settings' alias")

        # Banking alias
        banking_submodules = [m for m in visible_modules if m and (
            'banking' in m.strip().lower() or
            'reconciliation' in m.strip().lower()
        )]
        if banking_submodules and 'Banking' not in visible_modules and alias_allowed('Banking'):
            visible_modules.append('Banking')
            logger.debug("[OK] [ALIAS] Added 'Banking' parent alias")

    except Exception as e:
        logger.error(f"[ERROR] [CONTEXT] Error processing module aliases: {e}", exc_info=True)

    return visible_modules


def _compute_permission_flags(user_permissions, user, visible_modules=None):
    """
    COMPLETE FIX: Compute permission flags with license filtering
    Now includes check_module_permission() helper to prevent Masters menu bypass
    """

    # Sales flags
    # Require the Sales parent alias to be present to show Sales menu items
    sales_present = 'Sales' in (visible_modules or [])
    can_view_quotations = sales_present and any([
        user_permissions.get('Sales Quotation', {}).get('View', False),
        user_permissions.get('Sales Quotation', {}).get('Full Access', False),
    ])

    can_view_orders = sales_present and any([
        user_permissions.get('Sales Orders', {}).get('View', False),
        user_permissions.get('Sales Orders', {}).get('Full Access', False),
    ])

    can_view_invoices = sales_present and any([
        user_permissions.get('Sales Invoice', {}).get('View', False),
        user_permissions.get('Sales Invoice', {}).get('Full Access', False),
    ])

    can_view_payments_received = sales_present and any([
        user_permissions.get('Sales Payments Received', {}).get('View', False),
        user_permissions.get('Sales Payments Received', {}).get('Full Access', False),
    ])

    # Sales Delivery (template expects `can_view_delivery`)
    can_view_delivery = sales_present and any([
        user_permissions.get('Sales Delivery', {}).get('View', False),
        user_permissions.get('Sales Delivery', {}).get('Full Access', False),
        user_permissions.get('Sales Delivery Note', {}).get('View', False),
        user_permissions.get('Sales Delivery Note', {}).get('Full Access', False),
    ])

    # Sales Dashboard
    can_view_sales_dashboard = any([
        user_permissions.get('Sales Dashboard', {}).get('View', False),
        user_permissions.get('Sales Dashboard', {}).get('Full Access', False),
        user_permissions.get('Dashboard', {}).get('View', False),
        user_permissions.get('Dashboard', {}).get('Full Access', False),
    ])

    # Sales Return
    can_view_returns = sales_present and any([
        user_permissions.get('Sales Return', {}).get('View', False),
        user_permissions.get('Sales Return', {}).get('Full Access', False),
        user_permissions.get('Returns', {}).get('View', False),
        user_permissions.get('Returns', {}).get('Full Access', False),
    ])

    can_create_returns = sales_present and any([
        user_permissions.get('Sales Return', {}).get('Create', False),
        user_permissions.get('Sales Return', {}).get('Full Access', False),
        user_permissions.get('Returns', {}).get('Create', False),
        user_permissions.get('Returns', {}).get('Full Access', False),
    ])

    can_edit_returns = sales_present and any([
        user_permissions.get('Sales Return', {}).get('Edit', False),
        user_permissions.get('Sales Return', {}).get('Full Access', False),
        user_permissions.get('Returns', {}).get('Edit', False),
        user_permissions.get('Returns', {}).get('Full Access', False),
    ])

    can_delete_returns = sales_present and any([
        user_permissions.get('Sales Return', {}).get('Delete', False),
        user_permissions.get('Sales Return', {}).get('Full Access', False),
        user_permissions.get('Returns', {}).get('Delete', False),
        user_permissions.get('Returns', {}).get('Full Access', False),
    ])

    # Sales Performa Invoice
    can_view_performa_invoice = sales_present and any([
        user_permissions.get('Sales Performa Invoice', {}).get('View', False),
        user_permissions.get('Sales Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoice', {}).get('View', False),
        user_permissions.get('Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoices', {}).get('View', False),
        user_permissions.get('Performa Invoices', {}).get('Full Access', False),
    ])

    can_create_performa_invoice = sales_present and any([
        user_permissions.get('Sales Performa Invoice', {}).get('Create', False),
        user_permissions.get('Sales Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoice', {}).get('Create', False),
        user_permissions.get('Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoices', {}).get('Create', False),
        user_permissions.get('Performa Invoices', {}).get('Full Access', False),
    ])

    can_edit_performa_invoice = sales_present and any([
        user_permissions.get('Sales Performa Invoice', {}).get('Edit', False),
        user_permissions.get('Sales Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoice', {}).get('Edit', False),
        user_permissions.get('Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoices', {}).get('Edit', False),
        user_permissions.get('Performa Invoices', {}).get('Full Access', False),
    ])

    can_delete_performa_invoice = sales_present and any([
        user_permissions.get('Sales Performa Invoice', {}).get('Delete', False),
        user_permissions.get('Sales Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoice', {}).get('Delete', False),
        user_permissions.get('Performa Invoice', {}).get('Full Access', False),
        user_permissions.get('Performa Invoices', {}).get('Delete', False),
        user_permissions.get('Performa Invoices', {}).get('Full Access', False),
    ])

    # HR flags
    # HR menu requires HR parent alias
    hr_present = 'HR' in (visible_modules or [])
    can_view_dashboard = hr_present and any([
        user_permissions.get('HR Dashboard', {}).get('View', False),
        user_permissions.get('HR Dashboard', {}).get('Full Access', False),
        user_permissions.get('HR', {}).get('View', False),
        user_permissions.get('HR', {}).get('Full Access', False),
    ])

    can_view_employees = hr_present and any([
        user_permissions.get('HR Employee', {}).get('View', False),
        user_permissions.get('HR Employee', {}).get('Full Access', False),
        user_permissions.get('HR', {}).get('View', False),
        user_permissions.get('HR', {}).get('Full Access', False),
    ])

    can_view_recruitment = hr_present and any([
        user_permissions.get('HR Recruitment', {}).get('View', False),
        user_permissions.get('HR Recruitment', {}).get('Full Access', False),
        user_permissions.get('HR Recruitments', {}).get('View', False),
        user_permissions.get('HR Recruitments', {}).get('Full Access', False),
        user_permissions.get('HR', {}).get('View', False),
        user_permissions.get('HR', {}).get('Full Access', False),
    ])

    # HR Masters should depend on HR visibility and HR master aliases, not global Masters menu
    can_view_master = hr_present and any([
        user_permissions.get('HR Master', {}).get('View', False),
        user_permissions.get('HR Master', {}).get('Full Access', False),
        user_permissions.get('HR Masters', {}).get('View', False),
        user_permissions.get('HR Masters', {}).get('Full Access', False),
        user_permissions.get('HR masters', {}).get('View', False),
        user_permissions.get('HR masters', {}).get('Full Access', False),
        user_permissions.get('HR', {}).get('View', False),
        user_permissions.get('HR', {}).get('Full Access', False),
    ])

    # KEY FIX: Helper function to check module exists before calling permission function
    def check_module_permission(module_name, permission_func):
        """Only call permission function if module is in user_permissions (license-filtered)"""
        if module_name not in user_permissions:
            return False
        return permission_func(user)

    # MASTERS PERMISSIONS - NOW LICENSE-AWARE
    return {
        'can_view_quotations': can_view_quotations,
        'can_view_orders': can_view_orders,
        'can_view_invoices': can_view_invoices,
        'can_view_payments_received': can_view_payments_received,
        'can_view_delivery': can_view_delivery,
        'can_view_sales_dashboard': can_view_sales_dashboard,
        'can_view_performa_invoice': can_view_performa_invoice,
        'can_create_performa_invoice': can_create_performa_invoice,
        'can_edit_performa_invoice': can_edit_performa_invoice,
        'can_delete_performa_invoice': can_delete_performa_invoice,
        'can_view_returns': can_view_returns,
        'can_create_returns': can_create_returns,
        'can_edit_returns': can_edit_returns,
        'can_delete_returns': can_delete_returns,
        'can_view_dashboard': can_view_dashboard,
        'can_view_employees': can_view_employees,
        'can_view_recruitment': can_view_recruitment,
        'can_view_master': can_view_master,
        'can_view_items': check_module_permission('Masters Items', items_can_view),
        'can_create_items': check_module_permission('Masters Items', items_can_create),
        'can_edit_items': check_module_permission('Masters Items', items_can_edit),
        'can_delete_items': check_module_permission('Masters Items', items_can_delete),
        'can_view_categories': check_module_permission('Masters Category', can_view_categories),
        'can_create_categories': check_module_permission('Masters Category', can_create_categories),
        'can_edit_categories': check_module_permission('Masters Category', can_edit_categories),
        'can_delete_categories': check_module_permission('Masters Category', can_delete_categories),
        'can_view_types': check_module_permission('Masters Type', can_view_types),
        'can_create_types': check_module_permission('Masters Type', can_create_types),
        'can_edit_types': check_module_permission('Masters Type', can_edit_types),
        'can_delete_types': check_module_permission('Masters Type', can_delete_types),
        'can_view_customers': check_module_permission('Masters Customer', can_view_customers),
        'can_view_users': check_module_permission('Masters Users', can_view_users),
        'can_view_user_roles': check_module_permission('Masters User Roles', can_view_user_roles),
        'can_view_warehouse': check_module_permission('Masters Warehouse', can_view_warehouse),
        'can_create_warehouse': check_module_permission('Masters Warehouse', can_create_warehouse),
        'can_edit_warehouse': check_module_permission('Masters Warehouse', can_edit_warehouse),
        'can_delete_warehouse': check_module_permission('Masters Warehouse', can_delete_warehouse),
        'can_view_vendors': check_module_permission('Masters vendor', can_view_vendors),
        'can_create_vendors': check_module_permission('Masters vendor', can_create_vendors),
        'can_edit_vendors': check_module_permission('Masters vendor', can_edit_vendors),
        'can_delete_vendors': check_module_permission('Masters vendor', can_delete_vendors),
        'can_view_taxes': check_module_permission('Masters Taxes', can_view_taxes),
        'can_create_taxes': check_module_permission('Masters Taxes', can_create_taxes),
        'can_edit_taxes': check_module_permission('Masters Taxes', can_edit_taxes),
        'can_delete_taxes': check_module_permission('Masters Taxes', can_delete_taxes),
        'can_view_stock': check_module_permission('Masters Stock', can_view_stock),
        'can_create_stock': check_module_permission('Masters Stock', can_create_stock),
        'can_edit_stock': check_module_permission('Masters Stock', can_edit_stock),
        'can_delete_stock': check_module_permission('Masters Stock', can_delete_stock),
        'can_view_payterms': check_module_permission('Masters Payment Terms', can_view_payterms),
        'can_create_payterms': check_module_permission('Masters Payment Terms', can_create_payterms),
        'can_edit_payterms': check_module_permission('Masters Payment Terms', can_edit_payterms),
        'can_delete_payterms': check_module_permission('Masters Payment Terms', can_delete_payterms),
        'can_view_brands': check_module_permission('Masters Brand', can_view_brands),
        'can_create_brands': check_module_permission('Masters Brand', can_create_brands),
        'can_edit_brands': check_module_permission('Masters Brand', can_edit_brands),
        'can_delete_brands': check_module_permission('Masters Brand', can_delete_brands),
        'can_view_units': check_module_permission('Masters Unit', can_view_units),
        'can_create_units': check_module_permission('Masters Unit', can_create_units),
        'can_edit_units': check_module_permission('Masters Unit', can_edit_units),
        'can_delete_units': check_module_permission('Masters Unit', can_delete_units),

        # Banking flags
        'can_view_banking': can_view_banking(user),
        'can_create_banking': can_create_banking(user),
        'can_edit_banking': can_edit_banking(user),
        'can_delete_banking': can_delete_banking(user),
        'can_view_reconciliation': can_view_reconciliation(user),
        'can_create_reconciliation': can_create_reconciliation(user),
        'can_edit_reconciliation': can_edit_reconciliation(user),
        'can_delete_reconciliation': can_delete_reconciliation(user),

        # MIS flags
        'can_view_mis_dashboard': mis_can_view_dashboard(user),
        'can_view_mis_sales': mis_can_view_sales(user),
        'can_view_mis_purchase': mis_can_view_purchase(user),
        'can_view_mis_inventory': mis_can_view_inventory(user),
        'can_view_mis_finance': mis_can_view_finance(user),
        'can_view_mis_crm': mis_can_view_crm(user),
        'can_view_mis_hr': mis_can_view_hr(user),
        'can_view_mis_expense': mis_can_view_expense(user),
        'can_export_mis_reports': mis_can_export(user),
    }
