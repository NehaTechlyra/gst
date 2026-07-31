from django.shortcuts import redirect, render
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.urls import reverse, resolve
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.template import TemplateDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User as DjangoUser
import logging
import re
import inspect

try:
    from user.utils import has_permission
except Exception:
    def has_permission(user, module_name, permission_type):
        try:
            from user.utils import has_permission as _has_permission
            return _has_permission(user, module_name, permission_type)
        except Exception:
            logger.exception('Failed to import has_permission')
            return False

try:
    from Lyraerp.utils.db_utils import (
        register_database,
        sync_auth_user,
        ensure_required_modules,
        ensure_admin_role_permissions_up_to_date,
        ensure_sales_return_permissions,
        ensure_purchase_return_permissions,
        ensure_sales_performa_invoice_permissions,
        ensure_sales_eway_bill_permissions,
    )
except Exception:
    # Provide safe fallbacks to avoid NameError at runtime if import fails
    def register_database(db_name):
        logger.debug(f"register_database no-op for {db_name}")

    def sync_auth_user(user, db_name):
        logger.debug(f"sync_auth_user no-op for {user} -> {db_name}")

    def ensure_required_modules(db_name):
        logger.warning(f"ensure_required_modules not available for {db_name}")
        return False

    def ensure_admin_role_permissions_up_to_date(db_name):
        logger.debug(f"ensure_admin_role_permissions_up_to_date no-op for {db_name}")

    def ensure_sales_return_permissions(db_name):
        logger.debug(f"ensure_sales_return_permissions no-op for {db_name}")

    def ensure_purchase_return_permissions(db_name):
        logger.debug(f"ensure_purchase_return_permissions no-op for {db_name}")

    def ensure_sales_performa_invoice_permissions(db_name):
        logger.debug(f"ensure_sales_performa_invoice_permissions no-op for {db_name}")

    def ensure_sales_eway_bill_permissions(db_name):
        logger.debug(f"ensure_sales_eway_bill_permissions no-op for {db_name}")
from Lyraerp.utils.thread_locals import set_current_db, clear_current_db
from Lyraerp.utils.thread_locals import set_current_company_code, clear_current_company_code

logger = logging.getLogger(__name__)

# ============================================================================
# SHARED CONSTANTS
# ============================================================================

COMPANY_CODE_REGEX = re.compile(r'^/([A-Z0-9-]+)/')
ADMIN_PATH_REGEX = re.compile(r'^/(?:[A-Z0-9-]+/)?admin(?:/|$)')

EXEMPT_PATHS = [
    '/admin/',
    '/static/',
    '/media/',
    '/login/',
    '/logout/',
    '/signup/',
    '/Signup/',
    '/check-email/',
    '/check-username/',
    '/api/',
]

# Safe URL prefixes that don't require permission checks
SAFE_PREFIXES = {'api', 'static', 'health', 'favicon.ico'}

# ✅ FIX: Fragment-based exempt list for license/activation paths.
# Uses 'in' matching so it works with company-code-prefixed URLs like:
#   /KTKIMPEX-2026-9S9Y/activate-license/   → contains 'activate-license' ✓
#   /KTKIMPEX-2026-9S9Y/license/restricted/  → contains 'license/restricted' ✓
LICENSE_EXEMPT_FRAGMENTS = (
    'activate-license',
    'license/restricted',
    'license/',
    'trial-expired',
    'trail-expired',
    'trail_expired',
    'activity/new_logs/',
    # Profile/edit/password pages should remain reachable during license/trial flows
    'user/profile',
    'user/edit',
    'user/user/',
    'user/change_password',
    'user/delete',
)

# ============================================================================
# SHARED HELPER FUNCTIONS
# ============================================================================

def get_allowed_auth_urls():
    """Get set of allowed authentication URLs (login, logout)."""
    try:
        return {reverse('login'), reverse('logout')}
    except Exception:
        return set()


def is_exempt_path(path):
    """Check if path is in exempt paths (admin, static, media, auth)."""
    return is_admin_path(path) or any(path.startswith(exempt) for exempt in EXEMPT_PATHS)


def is_admin_path(path):
    """Check if path is a plain or company-code-prefixed Django admin URL."""
    return bool(ADMIN_PATH_REGEX.match(path or ''))


def is_license_exempt_path(path):
    """
    Check if path is a license/activation page that should always be accessible.
    Uses fragment matching to handle company-code-prefixed URLs like:
      /KTKIMPEX-2026-9S9Y/activate-license/
      /KTKIMPEX-2026-9S9Y/license/restricted/
    """
    return any(fragment in path for fragment in LICENSE_EXEMPT_FRAGMENTS)


def is_static_or_media_path(path):
    """Check if path is static or media."""
    return path.startswith(settings.STATIC_URL) or path.startswith('/media/')


def is_company_setup_path(path):
    """Check if path is a company setup path (with company code prefix)."""
    return bool(re.match(r'^/[A-Z0-9-]+/company/setup/', path))


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return (
        user and 
        getattr(user, 'is_authenticated', False) and 
        (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))
    )


def get_first_path_segment(path, skip_company_code=True):
    """
    Extract first meaningful path segment from URL.
    
    Args:
        path: URL path
        skip_company_code: If True, skip company code segment (default: True)
    
    Returns:
        First segment after company code (if skip_company_code=True) or first segment
    """
    segments = path.strip('/').split('/')
    
    if not segments:
        return ''
    
    # If skip_company_code and first segment looks like company code, use second segment
    if skip_company_code and len(segments) > 0 and re.match(r'^[A-Z0-9-]+$', segments[0]):
        return segments[1] if len(segments) > 1 else ''
    
    return segments[0]


def check_module_permissions(user, module_list, module_type=''):
    """
    Check if user has View permission for any module in the list.
    
    Args:
        user: Django user object
        module_list: List of module names to check
        module_type: Optional module type for logging (e.g., 'Purchase', 'Sales')
    
    Returns:
        True if user has permission for any module, False otherwise
    """
    for module in module_list:
        if has_permission(user, module, 'View'):
            if module_type:
                logger.debug(f'[MIDDLEWARE] User {user} allowed to access {module_type} (has {module} permission)')
            return True
    return False


def get_company_code_from_request(request):
    """
    Get company code from request (from attribute, session, or database).
    
    Args:
        request: Django request object
    
    Returns:
        Company code string or None
    """
    # Try request attribute first
    if hasattr(request, 'company_code') and request.company_code:
        return request.company_code
    
    # Try session
    company_code = request.session.get('company_code')
    if company_code:
        return company_code
    
    # Try database
    if request.user.is_authenticated:
        try:
            from user.models import User as CustomUser
            
            custom_user = CustomUser.objects.using('default').select_related(
                'usr_roleid__company'
            ).filter(usr_name=request.user.username).first()
            
            if custom_user and custom_user.usr_roleid and custom_user.usr_roleid.company:
                company = custom_user.usr_roleid.company
                company_code = company.company_code
                
                # Cache in session
                if company_code:
                    request.session['company_code'] = company_code
                    request.session.modified = True
                
                return company_code
        
        except Exception as e:
            logger.error(f"Error getting company code from DB: {e}")
    
    return None


# Alias for compatibility with existing code
REDIRECT_EXEMPT_PATHS = EXEMPT_PATHS


# ============================================================================
# MIDDLEWARE CLASSES
# ============================================================================

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow login, logout, signup, and static/media URLs without login
        allowed_urls = get_allowed_auth_urls()
        # Paths that should be allowed for unauthenticated users (exact or prefix)
        allowed_paths = ['/Signup/', '/signup/', '/password-reset/', '/reset/', '/login/', '/<str:company_code>/login/']

        if is_static_or_media_path(request.path) or is_admin_path(request.path):
            return self.get_response(request)
        
        # Allow company setup paths (with company code prefix)
        if is_company_setup_path(request.path):
            return self.get_response(request)
        
        if not request.user.is_authenticated:
            # Check if user has setup_company_id in session (post-signup)
            setup_company_id = request.session.get('setup_company_id')
            
            # Allow if path equals an allowed auth url OR starts with any allowed path prefix
            path_allowed = (request.path in allowed_urls) or any(request.path.startswith(p) for p in allowed_paths)

            # ✅ FIX: Allow login paths with company code pattern (/<COMPANY_CODE>/login/)
            if not path_allowed and not request.path.startswith('/static/'):
                company_code_login_match = re.match(r'^/[A-Z0-9-]+/login/?$', request.path)
                if company_code_login_match:
                    path_allowed = True

            if not path_allowed and not request.path.startswith('/static/'):
                # Allow access if they're in the setup flow with a valid session
                if setup_company_id and re.match(r'^/[A-Z0-9-]+/company/', request.path):
                    return self.get_response(request)
                
                # ✅ FIX: When redirecting to login after session timeout, prefer company-prefixed path
                company_code = get_company_code_from_request(request)
                if company_code:
                    # Redirect to /<company_code>/login/ instead of /login/
                    return redirect(f'/{company_code}/login/')
                else:
                    # Fallback to plain /login/
                    return redirect('/login/')
        return self.get_response(request)


class SiteBlockMiddleware:
    """Block access site-wide when settings.SITE_BLOCK is True.

    Behavior:
    - If SITE_BLOCK is False: do nothing.
    - Allow static/media/admin/login/logout and health-check paths.
    - Allow staff/superuser users to bypass the block.
    - All other requests return a simple blocked page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only active when explicitly turned on
        site_block = getattr(settings, 'SITE_BLOCK', False)
        logger.debug('SiteBlockMiddleware: SITE_BLOCK=%s path=%s user=%s', site_block, request.path, getattr(request, 'user', None))
        
        if not site_block:
            logger.debug('SiteBlockMiddleware: not active, passing through')
            return self.get_response(request)

        # Always allow static/media and admin paths
        path = request.path
        if is_static_or_media_path(path) or is_admin_path(path):
            logger.debug('SiteBlockMiddleware: allowed static/media/admin path: %s', path)
            return self.get_response(request)

        # Allow login/logout
        if path in get_allowed_auth_urls():
            logger.debug('SiteBlockMiddleware: allowed auth path: %s', path)
            return self.get_response(request)

        # Superusers and staff bypass the block
        if is_staff_or_superuser(request.user):
            logger.debug('SiteBlockMiddleware: user %s is staff/superuser, bypassing', request.user)
            return self.get_response(request)

        # Render a simple blocked page
        logger.debug('SiteBlockMiddleware: blocking request for path=%s user=%s', path, getattr(request, 'user', None))
        return render(request, 'site_blocked.html', status=403)


class ModulePermissionMiddleware(MiddlewareMixin):
    """Block access to app modules by URL first-segment when user lacks 'View' permission.

    This middleware infers the target module name from the first path segment
    (e.g. `/Items/` -> module `Items`) and checks `has_permission(user, module, 'View')`.
    If the user doesn't have view permission, they see the `site_blocked.html` page.
    """
    
    def _block_access(self, request, module_name, user):
        """Helper to log and return blocked response."""
        logger.debug('ModulePermissionMiddleware: user %s blocked from %s', user, module_name)
        return render(
            request,
            'site_blocked.html',
            {
                'restriction_type': 'permission',
                'blocked_module': module_name,
                'contact_email': 'lyraerp@techlyra.com',
                'company_code': getattr(request, 'company_code', None),
            },
            status=403,
        )
    
    def process_request(self, request):
        path = request.path or ''
        
        # Skip when not configured or not active
        if not getattr(settings, 'ENABLE_MODULE_PERMISSION_MIDDLEWARE', True):
            return None

        # Allow static/media/admin and auth paths
        if is_static_or_media_path(path) or is_admin_path(path):
            return None

        if path in get_allowed_auth_urls():
            return None

        # CRITICAL: Exempt company setup paths (with company code prefix)
        if is_company_setup_path(path):
            return None

        # ✅ CRITICAL FIX: Exempt license/activation paths using fragment matching.
        # This handles company-code-prefixed URLs like:
        #   /KTKIMPEX-2026-9S9Y/activate-license/   → 'activate-license' in path ✓
        #   /KTKIMPEX-2026-9S9Y/license/restricted/  → 'license/restricted' in path ✓
        # Without this, 'activate-license' and 'license' get extracted as module
        # names and the user is blocked with a 403 before reaching the view.
        if is_license_exempt_path(path):
            logger.debug('ModulePermissionMiddleware: license-exempt path, allowing: %s', path)
            return None

        # Get first path segment as module name (skip company code if present)
        seg = get_first_path_segment(path, skip_company_code=True)
        
        if not seg:
            return None

        # Common safe prefixes to ignore
        if seg.lower() in SAFE_PREFIXES:
            return None

        # Allow unrestricted access to the Currencies module (handled separately)
        if seg.lower() == 'currencies':
            return None
        
        # Allow AJAX requests to bank module (for adding banks in company setup)
        if seg.lower() == 'bank' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None

        # If user is not authenticated or is superuser/staff, allow or block accordingly
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            # Let LoginRequiredMiddleware handle unauthenticated redirects
            return None
        
        if is_staff_or_superuser(user):
            return None

        # Normalize common URL segments to the module names used in RolePermission.module.name
        lower_seg = seg.replace('-', '_').lower()
        path_lower = path.lower()
        
        # ========================================
        # VENDOR CHECK (BEFORE PURCHASE)
        # ========================================
        if 'vendor' in path_lower:
            # Allow explicit Masters vendor view permission
            if has_permission(user, 'Masters vendor', 'View'):
                return None

            # Also allow users who have Purchase-related permissions so that
            # Purchase users can select/create vendors when creating bills.
            if check_module_permissions(user, [
                'Purchase', 'Purchase Bills', 'Purchase Order', 'Purchase Payments Made', 'Purchase Delivery'
            ], 'Purchase'):
                return None

            return self._block_access(request, 'Masters vendor', user)

        # ========================================
        # ITEM HSN AJAX helper — allow from Purchase/Sales flows
        # ========================================
        # The endpoint '/Items/get-item-hsn/' is used by Purchase and Sales pages
        # to populate HSN for a selected item. Allow access if the user has
        # Purchase- or Sales-related permissions so creating bills/invoices
        # doesn't require full Masters Items permission.
        if 'get-item-hsn' in path_lower or 'hsn-codes' in path_lower:
            # Allow Purchase users
            if check_module_permissions(user, [
                'Purchase', 'Purchase Bills', 'Purchase Order', 'Purchase Payments Made', 'Purchase Delivery'
            ], 'Purchase'):
                return None

            # Allow Sales users
            if check_module_permissions(user, [
                'Sales', 'Sales Invoice', 'Sales Orders', 'Sales Quotation', 'Sales Delivery'
            ], 'Sales'):
                return None

        # Allow miscellaneous Items helper endpoints (unit, uom, brand, category, tax groups, etc.)
        items_helper_paths = [
            'uom', 'unit', 'brand', 'category', 'item-type', 'tax-groups', 'inter-state-taxes', 'sac-codes',
            'create-item-ajax', 'create-item-ajax-sales', 'create_item'
        ]
        if '/items/' in path_lower or path_lower.startswith('items/'):
            for helper in items_helper_paths:
                if helper in path_lower:
                    if check_module_permissions(user, [
                        'Purchase', 'Purchase Bills', 'Purchase Order', 'Purchase Payments Made', 'Purchase Delivery'
                    ], 'Purchase'):
                        return None
                    if check_module_permissions(user, [
                        'Sales', 'Sales Invoice', 'Sales Orders', 'Sales Quotation', 'Sales Delivery'
                    ], 'Sales'):
                        return None
                    break

            # Otherwise fallthrough to normal Masters Items check below and block
        
        # ========================================
        # ACCOUNTS & REPORTS
        # ========================================
        if 'account' in lower_seg or 'chart' in lower_seg:
            
                 # Allow report users to open account drill-down pages reached from reports,
            # even when they don't have generic Accounts module permission.
            if '/chart_of_accounts/detail/' in path_lower:
                report_modules = [
                    'Reports Balance Sheet',
                    'Reports Profit and Loss',
                    'Reports Trial Balance',
                    'Reports Cash Flow',
                    'Reports',
                ]
                if check_module_permissions(user, report_modules, 'Reports'):
                    return None
            # Allow report users to open party drill-down pages from account ledger.
            if '/chart_of_accounts/party/' in path_lower:
                report_modules = [
                    'Reports Balance Sheet',
                    'Reports Profit and Loss',
                    'Reports Trial Balance',
                    'Reports Cash Flow',
                    'Reports',
                ]
                if check_module_permissions(user, report_modules, 'Reports'):
                    return None
            if any(report_path in path_lower for report_path in [
                'balance-sheet', 'balance_sheet',
                'profit-loss', 'profit_loss',
                'trial-balance', 'trial_balance',
                'cash-flow', 'cash_flow',
                'inventory-valuation-summary', 'inventory_valuation_summary',
            ]):
                module_name = 'Reports'
            else:
                module_name = 'Accounts'
        
        # ========================================
        # JOURNAL
        # ========================================
        elif 'journal' in lower_seg:
            # Allow report users to open linked journal detail pages only.
            if re.search(r'/journal/journals/\d+/?$', path_lower):
                report_modules = [
                    'Reports Balance Sheet',
                    'Reports Profit and Loss',
                    'Reports Trial Balance',
                    'Reports Cash Flow',
                    'Reports',
                ]
                if check_module_permissions(user, report_modules, 'Reports'):
                    return None
            module_name = 'Journal'
        
        # ========================================
        # PAYMENT TERMS
        # ========================================
        elif 'payterm' in lower_seg:
            if has_permission(user, 'Sales', 'View') or has_permission(user, 'Masters Payment Terms', 'View') or has_permission(user, 'Sales Quotation', 'View') or has_permission(user, 'Sales Orders', 'View') or has_permission(user, 'Sales Order', 'View') or has_permission(user, 'Sales Invoice', 'View') or has_permission(user, 'Sales Performa Invoice', 'View'):
                return None
            return self._block_access(request, 'PayTerms', user)
        
        # ========================================
        # MASTERS MODULES
        # ========================================
        elif 'item' in lower_seg:
            module_name = 'Masters Items'
        elif 'designation' in lower_seg:
            if has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Designation'
        elif 'department' in lower_seg:
            if has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Department'
        elif 'allowance' in lower_seg:
            if has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Allowances'
        elif 'leave' in lower_seg:
            if has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Leaves'
        elif 'personaldocument' in lower_seg:
            if has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Personal Documents'
        elif 'warehouse' in lower_seg:
            module_name = 'Masters Warehouse'
        elif 'stock' in lower_seg:
            module_name = 'Masters Stock'
        elif 'tax' in lower_seg:
            module_name = 'Masters Taxes'
        elif 'brand' in lower_seg:
            module_name = 'Masters Brand'
        elif 'category' in lower_seg:
            # Category requires explicit Category module permission.
            if has_permission(user, 'Masters Category', 'View'):
                return None
            module_name = 'Masters Category'
        elif lower_seg == 'type':
            # Type requires explicit Type module permission.
            if has_permission(user, 'Masters Type', 'View'):
                return None
            module_name = 'Masters Type'
        elif 'unit' in lower_seg:
            module_name = 'Masters Unit'
        elif 'bank' in lower_seg:
            bank_path = path_lower
            if 'reconciliation' in bank_path:
                if has_permission(user, 'Bank Reconciliation', 'View'):
                    return None
                return self._block_access(request, 'Bank Reconciliation', user)
            elif 'banking' in bank_path or 'rules' in bank_path:
                if has_permission(user, 'Banking', 'View'):
                    return None
                return self._block_access(request, 'Banking', user)
            
            # Default fallback for bank master (add/edit/deactivate)
            if has_permission(user, 'Masters Bank', 'View') or has_permission(user, 'Masters', 'View'):
                return None
            module_name = 'Masters Bank'
        
        # ========================================
        # HR MODULE
        # ========================================
        elif lower_seg == 'hr':
            hr_modules = [
                'HR Dashboard',
                'HR Employee', 
                'HR masters',
                'HR Recruitments',
                'HR'
            ]
            if check_module_permissions(user, hr_modules, 'HR'):
                return None
            return self._block_access(request, 'HR', user)
        
        # ========================================
        # SALES MODULE
        # ========================================
        elif lower_seg == 'sales':
            # Enforce submodule-level permissions inside Sales based on URL.
            # This prevents one Sales submodule permission from unlocking all Sales pages.
            sales_subpath = path_lower

            # Default fallback: any explicit sales module view grants entry.
            required_modules = [
                'Sales Invoice',
                'Sales Orders',
                'Sales Order',
                'Sales Quotation',
                'Sales Payments Received',
                'Sales Delivery',
                'Sales',
            ]
            block_label = 'Sales'

            if 'payment' in sales_subpath:
                required_modules = ['Sales Payments Received', 'Payments Received', 'Sales']
                block_label = 'Sales Payments Received'
            elif 'dashboard' in sales_subpath:
                required_modules = ['Sales Dashboard']
                block_label = 'Sales Dashboard'
            elif 'delivery' in sales_subpath or '/returns/' in sales_subpath or '/return/' in sales_subpath:
                # Allow either Delivery or Return-related permissions to grant access.
                required_modules = [
                    'Sales Delivery',
                    'Sales Delivery Note',
                    'Delivery',
                    'Sales Return',
                    'Sales Returns',
                    'Returns',
                    'Sales',
                ]
                block_label = 'Sales Return'
            # Ensure "performa" paths are treated separately from regular invoices.
            # e.g. '/sales/performa-invoice/...' contains 'invoice' but refers to
            # Performa Invoice module, not Sales Invoice. Exclude performa here.
            elif (('invoice' in sales_subpath or 'sales_inv' in sales_subpath)
                  and 'performa' not in sales_subpath):
                required_modules = ['Sales Invoice', 'Invoices', 'Sales']
                block_label = 'Sales Invoice'
            elif 'order' in sales_subpath:
                required_modules = ['Sales Orders', 'Sales Order', 'Orders', 'Sales']
                block_label = 'Sales Order'
            elif 'quotation' in sales_subpath or 'quote' in sales_subpath:
                required_modules = ['Sales Quotation', 'Quotations', 'Sales']
                block_label = 'Sales Quotation'
            elif 'performa' in sales_subpath:
                required_modules = ['Sales Performa Invoice', 'Performa Invoice', 'Performa Invoices', 'Sales']
                block_label = 'Sales Performa Invoice'
            elif 'customer' in sales_subpath:
                required_modules = ['Masters Customer', 'Sales Customer', 'Customers', 'Sales', 'Sales Quotation', 'Sales Orders', 'Sales Order', 'Sales Invoice', 'Sales Performa Invoice']
                block_label = 'Sales Customer'
            elif 'eway' in sales_subpath:
                required_modules = ['Sales Eway Bill', 'E-Way Bills', 'Sales']
                block_label = 'Sales Eway Bill'

            if check_module_permissions(user, required_modules, 'Sales'):
                return None
            return self._block_access(request, block_label, user)
        
        # ========================================
        # MASTERS DASHBOARD (ROOT MASTERS SEGMENT)
        # ========================================
        elif lower_seg == 'masters':
            if 'master-dashboard' in path_lower:
                required_modules = ['Masters Dashboard']
                if check_module_permissions(user, required_modules, 'Masters'):
                    return None
                return self._block_access(request, 'Masters Dashboard', user)
            # Fallback for other masters routes
            if check_module_permissions(user, ['Masters'], 'Masters'):
                return None
            return self._block_access(request, 'Masters', user)

        # ========================================
        # CRM MODULE
        # ========================================
        elif lower_seg == 'crm':
            crm_modules = [
                'CRM Dashboard',
                'CRM Follow Ups',
                'CRM Lead',
                'CRM Lost reason',
                'CRM Opportunity',
                'CRM Presale',
                'CRM'
            ]
            if check_module_permissions(user, crm_modules, 'CRM'):
                return None
            return self._block_access(request, 'CRM', user)
        
        # ========================================
        # PURCHASE MODULE
        # ========================================
        elif 'purchase' in lower_seg:
            logger.debug(f'[MIDDLEWARE] Purchase module access attempt by {user} (path: {path})')
            purchase_subpath = path_lower

            # Dashboard should be gated by its own module permission.
            if 'dashboard' in purchase_subpath:
                required_modules = ['Purchase Dashboard']
                if check_module_permissions(user, required_modules, 'Purchase'):
                    return None
                logger.debug(f'[MIDDLEWARE] User {user} blocked from Purchase Dashboard')
                return self._block_access(request, 'Purchase Dashboard', user)

            purchase_modules = [
                'Purchase Order',
                'Purchase Bills',
                'Purchase Delivery',
                'Purchase Return',
                'Purchase Expenses',
                'Purchase Payments Made',
                'Purchase',
            ]

            if check_module_permissions(user, purchase_modules, 'Purchase'):
                return None

            logger.debug(f'[MIDDLEWARE] User {user} blocked from Purchase (no Purchase permissions)')
            return self._block_access(request, 'Purchase', user)
        
        
        # ========================================
        # SYSTEM SETTINGS
        # ========================================
        elif lower_seg == 'system_settings' or 'system' in lower_seg:
            system_modules = [
                'System settings',
                'System settings Company',
                'System settings Email Configuration',
                'System settings Email Templates',
                'System settings SMS Configuration',
                'System settings SMS Templates',
                'System settings Period Lock',
                'System',
            ]
            
            if check_module_permissions(user, system_modules, 'System'):
                logger.debug('ModulePermissionMiddleware: user %s allowed to access system_settings', user)
                return None
            
            logger.debug('ModulePermissionMiddleware: user %s blocked from system_settings (no System permission)', user)
            return self._block_access(request, 'system_settings', user)

        
        # ========================================
        # PRICE LIST
        # ========================================
        elif lower_seg in {'price-lists', 'price_lists', 'pricelist', 'pricelists'}:
            # Route segment uses "price-lists" or "pricelists" while role modules
            # are typically stored as "pricelist"/"Price List" variants.
            pricelist_modules = [
                'pricelist',
                'Price List',
                'Price Lists',
                'Sales Price List',
            ]
            if check_module_permissions(user, pricelist_modules, 'Price List'):
                return None
            return self._block_access(request, 'Price List', user)
        
        # ========================================
        # DEFAULT FALLBACK
        # ========================================
        else:
            module_name = seg.replace('_', ' ')
        
        # Check view permission
        try:
            if has_permission(user, module_name, 'View'):
                return None
        except Exception:
            logger.exception('ModulePermissionMiddleware: error checking permission for %s', module_name)
            return self._block_access(request, module_name, user)

        return self._block_access(request, module_name, user)


class CompanyDBMiddleware:
    """
    Sets request.company_db and syncs auth_user when needed.
    Handles multi-tenant database routing for both superadmins and regular users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _repair_company_modules(self, db_name):
        """Backfill missing tenant modules before request handling continues."""
        if not db_name or db_name == 'default':
            return

        try:
            added = ensure_required_modules(db_name)
            if added:
                ensure_admin_role_permissions_up_to_date(db_name)
                ensure_sales_eway_bill_permissions(db_name)
            # DISABLED: Do not auto-create return permissions on every request
            # This was causing Sales Return to appear when user only selected Sales Delivery
            # Users must explicitly select what permissions they want
            # ensure_sales_return_permissions(db_name)
            # ensure_purchase_return_permissions(db_name)
            # ensure_sales_performa_invoice_permissions(db_name)
        except Exception as exc:
            logger.warning(
                "[MIDDLEWARE] Failed module repair for %s: %s",
                db_name,
                exc,
            )

    def _setup_superadmin_db(self, request):
        """Setup database for superadmin users."""
        selected_company_db = request.session.get('company_db', 'default')
        selected_company_id = request.session.get('company_id')
        
        if selected_company_db and selected_company_db != 'default':
            register_database(selected_company_db)
            
            # Sync super admin auth_user to company DB
            try:
                django_user = DjangoUser.objects.using('default').get(
                    username=request.user.username
                )
                sync_auth_user(django_user, selected_company_db)
                logger.debug(f"[OK] Synced super admin to {selected_company_db}")
            except Exception as sync_error:
                logger.warning(f"[WARNING] Failed to sync super admin: {sync_error}")
            
            request.company_db = selected_company_db
            request.company_id = selected_company_id
            
            # Set thread-local for router
            set_current_db(selected_company_db)
            self._repair_company_modules(selected_company_db)
            
            logger.debug(f"[MIDDLEWARE] Super Admin using DB: {selected_company_db}")
        else:
            logger.debug(f"[MIDDLEWARE] Super Admin using master DB")

    def _setup_regular_user_db(self, request):
        """Setup database for regular users."""
        from user.models import User
        
        custom_user = User.objects.using('default').select_related(
            'usr_roleid__company'
        ).filter(usr_name=request.user.username).first()
        
        if custom_user:
            role = custom_user.usr_roleid
            if role and role.company and role.company.db_name:
                db_name = role.company.db_name
                register_database(db_name)
                
                request.company_db = db_name
                request.company_id = role.company.id
                
                # Set thread-local for router
                set_current_db(db_name)
                self._repair_company_modules(db_name)
                
                logger.debug(f"[MIDDLEWARE] User {request.user.username} using DB: {db_name}")
            else:
                logger.debug(f"[MIDDLEWARE] User has no company DB")
        else:
            logger.debug(f"[MIDDLEWARE] Custom user not found")

    def __call__(self, request):
        # Check if company_id is already set by CompanyCodeMiddleware
        if hasattr(request, 'company_id') and request.company_id:
            if hasattr(request, 'company_db') and request.company_db != 'default':
                register_database(request.company_db)
                set_current_db(request.company_db)
                self._repair_company_modules(request.company_db)
            try:
                response = self.get_response(request)
                return response
            finally:
                clear_current_db()
        
        request.company_db = "default"
        request.company_id = None
        
        # Set thread-local at the start
        set_current_db("default")
        
        try:
            if request.user.is_authenticated:
                try:
                    is_superadmin = request.session.get('is_superadmin', False)
                    
                    if is_superadmin:
                        self._setup_superadmin_db(request)
                    else:
                        self._setup_regular_user_db(request)
                        
                except Exception as e:
                    logger.error(f"[MIDDLEWARE ERROR] {e}", exc_info=True)
                    request.company_db = "default"
                    request.company_id = None
                    set_current_db("default")
            
            response = self.get_response(request)
            return response
            
        finally:
            # Clean up thread-local after request
            clear_current_db()


class ActivityLogMiddleware:
    """
    Middleware to automatically capture request context for activity logging.
    Stores IP address and user agent for use in signals.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request data for use in signals
        try:
            from activity_log.utils import get_client_ip, get_user_agent
            request._activity_log_ip = get_client_ip(request)
            request._activity_log_user_agent = get_user_agent(request)
        except Exception as e:
            logger.debug(f"ActivityLogMiddleware: Could not capture activity context: {e}")
        
        response = self.get_response(request)
        return response


class TemplateFallbackMiddleware:
    """
    Catch TemplateDoesNotExist and return a readable fallback instead of a blank page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except TemplateDoesNotExist as exc:
            message = f"Template not found: {exc}.\nPlease check template paths."
            logger.error(f"TemplateFallbackMiddleware: {message}")
            return HttpResponse(f"<pre>{message}</pre>", status=500)
        except Exception as e:
            logger.error(f"TemplateFallbackMiddleware: Unexpected error: {e}", exc_info=True)
            return HttpResponse(f"<pre>Server error: {e}</pre>", status=500)


class CompanyCodeMiddleware:
    """
    Extracts company code from URL and maps to company database.
    
    URL Pattern: /<COMPANY_CODE>/<path>/
    Example: /TECH4-14HG/sales/invoices/
    
    Sets:
    - request.company_code: The company code from URL
    - request.company_id: Company ID from database
    - request.company_db: Company database name
    - Thread-local company_code for URL reversing (⭐ CRITICAL FOR reverse())
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def _map_company_code_to_db(self, request, company_code):
        """Map company code to database and set request attributes."""
        try:
            from company.models import Company
            
            company = Company.objects.using('default').filter(
                company_code=company_code
            ).first()
            
            if company:
                # Set company info on request
                request.company_code = company_code
                request.company_id = company.id
                request.company_db = company.db_name if company.db_created else 'default'
                
                # ⭐ CRITICAL: Store in thread-local for reverse() to access
                set_current_company_code(company_code)
                
                logger.debug(f"[COMPANY URL] Mapped to: {company.name} (DB: {request.company_db})")
            else:
                logger.warning(f"[COMPANY URL] No company found for code: {company_code}")
                request.company_code = company_code
                request.company_id = None
                request.company_db = 'default'
                set_current_company_code(company_code)
        
        except Exception as e:
            logger.error(f"[COMPANY URL] Error mapping code: {e}")
            request.company_code = company_code
            request.company_id = None
            request.company_db = 'default'
            set_current_company_code(company_code)
    
    def __call__(self, request):
        # Check if path should be skipped
        if is_exempt_path(request.path):
            return self.get_response(request)
        
        # Extract company code from URL
        match = COMPANY_CODE_REGEX.match(request.path)
        
        if match:
            company_code = match.group(1)
            
            logger.debug(f"[COMPANY URL] Extracted code: {company_code}")
            
            # Store in session
            request.session['company_code'] = company_code
            request.session.modified = True
            
            # Map company code to database
            self._map_company_code_to_db(request, company_code)
        
        else:
            # No company code in URL
            request.company_code = None
            request.company_id = None
            request.company_db = 'default'
            clear_current_company_code()
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up thread-local after request
            clear_current_company_code()


class CompanyURLEnforcerMiddleware:
    """
    Ensures all URLs include company code for authenticated users.
    
    If user is logged in but URL doesn't have company code:
    - Get code from session or database
    - Redirect to URL with company code prefix
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip exempt paths
        if is_exempt_path(request.path):
            return self.get_response(request)
        
        # Skip favicon requests to avoid duplicate logging/redirects
        # Browser often requests /favicon.ico which is then redirected to
        # /<company_code>/favicon.ico causing two middleware runs and
        # duplicate log lines. Early-return for favicon paths.
        if 'favicon.ico' in (request.path or ''):
            return self.get_response(request)
        
        # Skip if not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip for superusers
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Check if URL already has company code
        if COMPANY_CODE_REGEX.match(request.path):
            # Already has company code - allow
            return self.get_response(request)
        
        # URL missing company code - get it
        company_code = get_company_code_from_request(request)
        
        # If we have a company code, redirect with it
        if company_code:
            # Build new path with company code
            new_path = f"/{company_code}{request.path}"
            
            # Preserve query string
            if request.META.get('QUERY_STRING'):
                new_path += f"?{request.META['QUERY_STRING']}"
            
            logger.debug(f"[COMPANY URL] Redirecting: {request.path} → {new_path}")
            return redirect_with_company(new_path)
        
        # No company code available - allow request (will be handled by other middleware)
        logger.warning(f"[COMPANY URL] No company code for user {request.user.username}")
        return self.get_response(request)


class ViewKwargFilterMiddleware(MiddlewareMixin):
    """
    Middleware that filters out company_code from view kwargs if the view doesn't accept it.
    
    Since all URLs are prefixed with <str:company_code>/, Django automatically passes this
    as a kwarg to every view. This middleware ensures only views that explicitly accept
    company_code receive it.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Remove company_code from kwargs if the view doesn't accept it."""
        if 'company_code' in view_kwargs:
            try:
                # Get the view function (unwrap if it's decorated)
                actual_func = view_func
                while hasattr(actual_func, '__wrapped__'):
                    actual_func = actual_func.__wrapped__
                
                # Check if the view accepts company_code parameter
                sig = inspect.signature(actual_func)
                if 'company_code' not in sig.parameters:
                    # View doesn't accept company_code, remove it
                    company_code = view_kwargs.pop('company_code', None)
                    # Store it in request for template access
                    if company_code and not hasattr(request, 'company_code'):
                        request.company_code = company_code
            except (ValueError, TypeError):
                # If we can't inspect, safely remove company_code
                company_code = view_kwargs.pop('company_code', None)
                if company_code and not hasattr(request, 'company_code'):
                    request.company_code = company_code
        
        return None


class AutoCompanyCodeRedirectMiddleware:
    """
    ✅ UNIVERSAL FIX: Automatically adds company_code to ALL redirects.
    
    This middleware intercepts redirect responses and automatically adds
    company_code to the URL if it's missing.
    
    NO NEED TO CHANGE ANY VIEW CODE!
    
    How it works:
    1. Intercepts HTTP redirect responses (302/301)
    2. Checks if redirect URL is missing company_code
    3. Adds company_code automatically
    4. Returns fixed redirect
    
    Installation:
    Add to MIDDLEWARE in settings.py AFTER CompanyCodeMiddleware:
        'Lyraerp.middleware.AutoCompanyCodeRedirectMiddleware',
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only process redirects
        if not isinstance(response, HttpResponseRedirect):
            return response
        
        # Get company code from request
        company_code = get_company_code_from_request(request)
        
        if not company_code:
            # No company code available, return as-is
            return response
        
        # Get the redirect URL
        redirect_url = response['Location']
        
        # Check if URL already has company code
        if f'/{company_code}/' in redirect_url:
            # Already has company code, return as-is
            return response
        
        # Check if this is an internal redirect (starts with /)
        if not redirect_url.startswith('/'):
            # External URL or fragment, return as-is
            return response
        
        # Check if this is an exempt path (login, logout, signup, static, etc.)
        if is_exempt_path(redirect_url):
            return response
        
        # Add company code to the redirect URL
        fixed_url = f'/{company_code}{redirect_url}'
        
        logger.debug(f"[AUTO-FIX REDIRECT] {redirect_url} → {fixed_url}")
        
        # Create new redirect with fixed URL
        return HttpResponseRedirect(fixed_url)


class TrialExpirationMiddleware:
    """
    Blocks access when company trial has expired and no valid license exists.
    
    Behavior:
    - Checks if user's company trial has expired
    - If expired and no valid license, renders 'trail_expired_page.html'
    - Allows staff/superuser to bypass the block
    - Allows static/media/admin/auth paths without checking
    - Allows company setup paths even if trial is expired
    
    Installation:
    Add to MIDDLEWARE in settings.py AFTER ModulePermissionMiddleware:
        'Lyraerp.middleware.TrialExpirationMiddleware',
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Explicit early allow: ensure activation and restricted pages are always reachable
        path = request.path or ''
        if 'activate-license' in path or 'license/restricted' in path:
            logger.debug("[TRIAL EXPIRATION] Allowing activation/restricted path: %s", path)
            return self.get_response(request)

        # Check if trial blocking is needed
        should_block = self._should_block_for_expired_trial(request)
        
        if should_block:
            logger.warning(
                f'[TRIAL EXPIRATION] Blocking access for {request.user} - '
                f'trial expired and no valid license'
            )
            try:
                return redirect_with_company(request, 'trial_expired_page')
            except Exception:
                company_code = getattr(request, 'company_code', None)
                if company_code:
                    return redirect(f'/{company_code}/trial-expired/')
                return render(request, 'trial_expired.html', status=403)
        
        return self.get_response(request)
    
    def _should_block_for_expired_trial(self, request):
        """
        Determine if request should be blocked due to expired trial.
        
        Returns False (allow) if:
        - User is unauthenticated
        - User is staff/superuser
        - Path is exempt (static, media, admin, auth, setup)
        - Company trial is still active or has valid license
        
        Returns True (block) if:
        - User is authenticated and not staff/superuser
        - Path is not exempt
        - Company trial is expired and has no valid license
        """
        path = request.path or ''
        logger.debug("[TRIAL DIAG] path=%s", path)
        
        # Allow unauthenticated users (LoginRequiredMiddleware will redirect to login)
        if not request.user.is_authenticated:
            return False
        
        # Allow staff/superuser
        if is_staff_or_superuser(request.user):
            logger.debug('[TRIAL EXPIRATION] Staff/superuser bypass')
            return False
        
        # Allow static/media/admin paths
        if is_static_or_media_path(path) or is_admin_path(path):
            return False
        
        # Allow auth paths
        if path in get_allowed_auth_urls():
            return False
        
        # Allow company setup paths (setup can proceed even if trial expired)
        if is_company_setup_path(path):
            return False
        
        # ✅ FIX: Use shared fragment-based license exempt check.
        # Replaces the old manual checks for '/activate-license/' and 'license/restricted'.
        license_exempt = is_license_exempt_path(path)
        logger.debug("[TRIAL DIAG] is_license_exempt_path=%s", license_exempt)
        if license_exempt:
            return False
        
        # Allow signup/login paths
        auth_paths = ['/signup/', '/Signup/', '/login/', '/logout/', '/check-email/', '/check-username/']
        if any(path.startswith(auth_path) for auth_path in auth_paths):
            return False
        
        # Allow API endpoints
        if path.startswith('/api/'):
            return False
        
        # Get user's company
        # If LicenseInfoMiddleware already ran it will have populated request.license_info.
        # Prefer using that to determine license validity (works when license is stored
        # in company DB rather than master DB).
        license_info = getattr(request, 'license_info', None)
        has_valid_license = False
        
        if license_info:
            has_license = license_info.get('has_license', False)
            is_valid = license_info.get('is_valid', False)
            is_expired = license_info.get('is_expired', False)
            
            # If we have a valid, active license, ALWAYS allow access
            if has_license and is_valid and not is_expired:
                logger.info("[TRIAL DIAG] request.license_info indicates valid license for %s — allowing access", getattr(request.user, 'username', 'unknown'))
                return False
            
            # Record status for fallback logic below
            has_valid_license = has_license and is_valid and not is_expired

        company = self._get_user_company(request)
        if not company:
            logger.debug('[TRIAL EXPIRATION] No company found for user')
            return False
        
        # Check if trial has expired
        try:
            trial_expired = company.check_trial_expired()
            # Also read trial_active flag (0 = regular mode, 1 = trial mode)
            trial_active = getattr(company, 'trial_active', True)
        except Exception as e:
            logger.exception("[TRIAL DIAG] Error checking trial status: %s", e)
            trial_expired = False
            trial_active = False

        # Fallback license check if request.license_info was missing or inconclusive
        if not has_valid_license:
            try:
                # Use the database context from the request (tenant DB)
                company_db = getattr(request, 'company_db', 'default')
                if company_db and company_db != 'default':
                    from company_settings.models import LicenseKey
                    # Direct check in tenant DB
                    has_valid_license = LicenseKey.objects.using(company_db).filter(
                        company_id=company.id, 
                        is_active=True,
                        is_license_expired=False
                    ).exists()
                    if has_valid_license:
                        logger.info("[TRIAL DIAG] Valid license found in tenant DB '%s' for %s", company_db, company.name)
            except Exception as e:
                logger.warning("[TRIAL DIAG] Fallback license check failed: %s", e)

        logger.info("[TRIAL DIAG] company='%s' trial_active=%s trial_expired=%s has_valid_license=%s",
                     company.name, trial_active, trial_expired, has_valid_license)

        # 1. If they have a valid license, they are NEVER blocked by trial logic
        if has_valid_license:
            logger.info("[TRIAL EXPIRATION] Bypass trial check: Valid license active for %s", company.name)
            return False

        # 2. If trial is not active (i.e. they are supposed to be in license mode or converted),
        # don't block them here — let LicenseCheckMiddleware handle the license gate.
        if not trial_active:
            logger.info("[TRIAL EXPIRATION] Bypass trial check: Trial mode is OFF for %s", company.name)
            return False

        # 3. If trial is active but not yet expired, allow access
        if (not trial_expired):
            logger.debug('[TRIAL EXPIRATION] Trial active and not expired for %s', company.name)
            return False
        
        # 4. Trial is active AND expired AND no valid license found — block access
        logger.warning(
            f'[TRIAL EXPIRATION] ❌ BLOCKING: Trial expired for company {company.name} '
            f'(expires_at: {company.trial_expires_at}) and no active license found.'
        )
        return True


    
    def _get_user_company(self, request):
        """
        Get the company associated with the request user.
        
        Returns: Company object or None
        """
        try:
            from user.models import User as CustomUser
            from company.models import Company
            
            # Try to get company from custom user
            custom_user = CustomUser.objects.using('default').select_related(
                'usr_roleid__company'
            ).filter(usr_name=request.user.username).first()
            
            if custom_user and custom_user.usr_roleid and custom_user.usr_roleid.company:
                return custom_user.usr_roleid.company
            
            # Fallback: try to get first active company
            return Company.objects.using('default').filter(status=True).first()
        
        except Exception as e:
            logger.error(f'[TRIAL EXPIRATION] Error getting user company: {e}')
            return None


class SessionTimeoutMiddleware:
    """
    Handles session timeout based on "Remember Me" checkbox.
    
    Behavior:
    - If remember_me=True: Session expires in 14 days (1209600 seconds)
    - If remember_me=False: Session expires in 15 minutes (900 seconds)
    
    How it works:
    1. LoginView sets remember_me flag in session and calls set_expiry()
    2. This middleware extends the session timeout on each request if remember_me=True
    3. If remember_me=False, session naturally expires after 900 seconds of inactivity
    
    Installation:
    Add to MIDDLEWARE in settings.py AFTER CompanyURLEnforcerMiddleware:
        'Lyraerp.middleware.SessionTimeoutMiddleware',
    """
    
    # Session timeout constants
    REMEMBER_ME_TIMEOUT = 1209600  # 14 days in seconds
    DEFAULT_TIMEOUT = 900  # 15 minutes in seconds
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is authenticated and has session data
        if request.user.is_authenticated:
            try:
                # Get remember_me flag from session
                remember_me = request.session.get('remember_me', False)
                
                # Extend session timeout if Remember Me is enabled
                if remember_me:
                    # Set expiry to 14 days for Remember Me sessions
                    request.session.set_expiry(self.REMEMBER_ME_TIMEOUT)
                    logger.debug(
                        f"[SESSION TIMEOUT] Extending session for user {request.user.username} "
                        f"(Remember Me: 14 days)"
                    )
                else:
                    # For non-Remember Me sessions, don't reset the timer on every request
                    # Let it naturally expire after 15 minutes of inactivity
                    logger.debug(
                        f"[SESSION TIMEOUT] Session timeout for user {request.user.username} "
                        f"set to 15 minutes"
                    )
            
            except Exception as e:
                logger.warning(f"[SESSION TIMEOUT] Error handling session timeout: {e}")
        
        response = self.get_response(request)
        return response
