# """
# License and Trial Middleware - COMPLETE INTEGRATED VERSION
# ===========================================================

# This middleware handles three critical functions:
# 1. LicenseInfoMiddleware - Loads license and trial information into every request
# 2. LicenseCheckMiddleware - Enforces license restrictions and trial expiry
# 3. First login flow - Redirects to company setup on first login

# INTEGRATION:
# -----------
# - Works with existing LicenseKey model from company_settings
# - Adds trial system for new companies without licenses
# - Maintains all existing license check logic
# - Prevents redirect loops on company setup pages

# FLOW:
# -----
# 1. User logs in
# 2. CompanyDBMiddleware sets request.company_db and request.company_id
# 3. LicenseInfoMiddleware loads:
#    - License data (from LicenseKey model)
#    - Trial data (from Company model)
#    - First login flag
# 4. LicenseCheckMiddleware decides:
#    - Valid license → Allow access
#    - First login → Redirect to /company/setup/
#    - Trial active and not expired → Allow access
#    - Trial expired and no license → Show trial_expired.html
#    - No license and not in trial → Show site_blocked.html

# VERSION: 5.0 - Integrated Trial System
# AUTHOR: System
# DATE: 2026-02-16
# """
# import logging
# from datetime import date, datetime
# from django.shortcuts import redirect, render
# from django.urls import reverse
# import re

# logger = logging.getLogger(__name__)


# class LicenseInfoMiddleware:
#     """
#     License and Trial Information Loader Middleware
#     ==============================================
    
#     Purpose:
#     --------
#     Injects license and trial information into every request for:
#     - Module filtering in sidebar
#     - Access control decisions
#     - UI customization based on license/trial status
#     - First-time login detection
    
#     This middleware does NOT block access - it only loads information.
#     The actual access blocking is done by LicenseCheckMiddleware.
    
#     Request Attributes Set:
#     ----------------------
#     request.license_info = {
#         # License Information (from LicenseKey model)
#         'has_license': bool,        # True if LicenseKey exists
#         'is_valid': bool,           # True if license exists and not expired
#         'is_expired': bool,         # True if license expired
#         'allowed_modules': list,    # List of module codes, None for full access
#         'max_users': int,           # Maximum users allowed
#         'license_key': str,         # The actual license key
#         'expiry_date': date,        # License expiration date
#         'license_type': str,        # 'none', 'standard', 'trial', 'superuser'
        
#         # Trial Information (from Company model)
#         'trial_active': bool,       # True if company in trial mode
#         'trial_expired': bool,      # True if trial has expired
#         'days_remaining': int,      # Days until trial expires (negative if expired)
#         'trial_message': str,       # Human-readable trial status
#         'trial_started_at': datetime, # When trial started
#         'trial_expires_at': datetime, # When trial expires
        
#         # Setup Information
#         'setup_complete': bool,     # True if company setup is complete
#         'is_first_login': bool,     # True if first_login_completed=False
#     }
    
#     Execution Order:
#     ---------------
#     This MUST run AFTER CompanyDBMiddleware which sets:
#     - request.company_db
#     - request.company_id
#     """
    
#     # URLs that don't need license checking
#     EXEMPT_PREFIXES = (
#         '/admin/',              # Django admin
#         '/static/',             # Static files (CSS, JS, images)
#         '/media/',              # User uploaded files
#         '/login/',              # Login page
#         '/logout/',             # Logout page
#         '/signup/',             # Signup page
#         '/Signup/',             # Signup page (case variation)
#         '/company/license/',    # License management
#         '/company/create/',     # Company creation
#         '/company/update/',     # Company update/edit
#         '/license/restricted/', # Site blocked page
#         '/activate-license/',   # License activation page
#         '/trial-expired/',      # Trial expired page
#     )
    
#     def __init__(self, get_response):
#         """Initialize middleware with Django's get_response callable."""
#         self.get_response = get_response
    
#     def __call__(self, request):
#         """Process each request to load license and trial information."""
        
#         # ============================================
#         # STEP 1: Initialize default license info
#         # ============================================
#         request.license_info = {
#             # License fields
#             'has_license': False,
#             'is_valid': False,
#             'is_expired': False,
#             'allowed_modules': [],
#             'max_users': 0,
#             'license_key': '',
#             'expiry_date': None,
#             'license_type': 'none',
            
#             # Trial fields
#             'trial_active': False,
#             'trial_expired': False,
#             'days_remaining': None,
#             'trial_message': '',
#             'trial_started_at': None,
#             'trial_expires_at': None,
            
#             # Setup fields
#             'setup_complete': False,
#             'is_first_login': True,
#         }
        
#         # ============================================
#         # STEP 2: Check if this URL should be skipped
#         # ============================================
#         if request.path.startswith(self.EXEMPT_PREFIXES):
#             logger.debug(f"[LICENSE INFO] Skipping exempt path: {request.path}")
#             return self.get_response(request)
        
#         # Skip company setup paths (with company code)
#         if re.match(r'^/[A-Z0-9-]+/company/setup/', request.path) or request.path.startswith('/company/setup/'):
#             logger.debug(f"[LICENSE INFO] Skipping company setup path: {request.path}")
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 3: Check if user is authenticated
#         # ============================================
#         if not request.user.is_authenticated:
#             logger.debug("[LICENSE INFO] Unauthenticated user - skipping")
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 4: Handle superusers (full access)
#         # ============================================
#         if request.user.is_superuser:
#             logger.debug(f"[LICENSE INFO] Superuser {request.user.username} - full access")
#             request.license_info = {
#                 'has_license': True,
#                 'is_valid': True,
#                 'is_expired': False,
#                 'allowed_modules': None,  # None = ALL modules
#                 'max_users': 999,
#                 'license_key': 'SUPERUSER',
#                 'expiry_date': None,
#                 'license_type': 'superuser',
#                 'trial_active': False,
#                 'trial_expired': False,
#                 'days_remaining': None,
#                 'trial_message': '',
#                 'setup_complete': True,
#                 'is_first_login': False,
#             }
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 5: Get company information
#         # ============================================
#         company_db = getattr(request, 'company_db', 'default')
#         company_id = getattr(request, 'company_id', None)
        
#         if not company_id:
#             logger.debug(f"[LICENSE INFO] No company_id for user {request.user.username}")
#             return self.get_response(request)
        
#         logger.debug(f"[LICENSE INFO] User: {request.user.username}, Company: {company_id}, DB: {company_db}")
        
#         # ============================================
#         # STEP 6: Check setup status and first login
#         # ============================================
#         setup_complete = self._check_setup_complete(company_id)
#         is_first_login = self._is_first_login(company_id)
        
#         request.license_info['setup_complete'] = setup_complete
#         request.license_info['is_first_login'] = is_first_login
        
#         logger.debug(f"[LICENSE INFO] Setup complete: {setup_complete}, First login: {is_first_login}")
        
#         # ============================================
#         # STEP 7: Load license from LicenseKey model
#         # ============================================
#         license_data = self._load_license_data(company_db, company_id)
        
#         # ============================================
#         # STEP 8: Load trial data from Company model
#         # ============================================
#         trial_data = self._load_trial_data(company_id)
        
#         # ============================================
#         # STEP 9: Merge license and trial data
#         # ============================================
#         request.license_info.update(license_data)
#         request.license_info.update(trial_data)
        
#         # ============================================
#         # STEP 10: Determine overall validity
#         # ============================================
#         # User has access if:
#         # 1. Valid license (not expired), OR
#         # 2. Trial active and not expired
        
#         has_valid_license = license_data.get('is_valid', False) and not license_data.get('is_expired', True)
#         trial_active_valid = trial_data.get('trial_active', False) and not trial_data.get('trial_expired', True)
        
#         request.license_info['is_valid'] = has_valid_license or trial_active_valid
        
#         # Determine license type
#         if has_valid_license:
#             request.license_info['license_type'] = 'licensed'
#         elif trial_active_valid:
#             request.license_info['license_type'] = 'trial'
#         else:
#             request.license_info['license_type'] = 'none'
        
#         logger.info(
#             f"[LICENSE INFO] Final status - "
#             f"Type: {request.license_info['license_type']}, "
#             f"Valid: {request.license_info['is_valid']}, "
#             f"Has License: {license_data.get('has_license')}, "
#             f"Trial: {trial_data.get('trial_active')}/{trial_data.get('trial_expired')}"
#         )
        
#         return self.get_response(request)
    
#     def _check_setup_complete(self, company_id):
#         """Check if company setup is complete."""
#         try:
#             from company.models import Company
#             company = Company.objects.using('default').get(id=company_id)
#             return company.setup_complete
#         except Exception as e:
#             logger.error(f"[LICENSE INFO] Error checking setup: {e}")
#             return False
    
#     def _is_first_login(self, company_id):
#         """Check if this is the user's first login."""
#         try:
#             from company.models import Company
#             company = Company.objects.using('default').get(id=company_id)
#             is_first = not bool(company.first_login_completed)
#             logger.debug(
#                 f"[LICENSE INFO] Company {company_id} - "
#                 f"first_login_completed: {company.first_login_completed}, "
#                 f"is_first_login: {is_first}"
#             )
#             return is_first
#         except Exception as e:
#             logger.error(f"[LICENSE INFO] Error checking first login: {e}")
#             return True  # Safer default
    
#     def _load_license_data(self, company_db, company_id):
#         """Load license data from LicenseKey model."""
#         license_data = {
#             'has_license': False,
#             'is_valid': False,
#             'is_expired': False,
#             'allowed_modules': [],
#             'max_users': 0,
#             'license_key': '',
#             'expiry_date': None,
#         }
        
#         try:
#             from company_settings.models import LicenseKey
            
#             try:
#                 license_obj = LicenseKey.objects.using(company_db).get(
#                     company_id=company_id,
#                     is_active=True
#                 )
                
#                 logger.info(f"[LICENSE INFO] ✅ Found active license for company {company_id}")
                
#                 # Check if expired
#                 is_expired = False
#                 if hasattr(license_obj, 'is_expired') and callable(license_obj.is_expired):
#                     is_expired = license_obj.is_expired()
#                 elif hasattr(license_obj, 'expiry_date') and license_obj.expiry_date:
#                     from datetime import date
#                     is_expired = date.today() > license_obj.expiry_date
                
#                 # Get allowed modules
#                 allowed_modules = self._get_allowed_modules(license_obj)
                
#                 license_data = {
#                     'has_license': True,
#                     'is_valid': not is_expired,
#                     'is_expired': is_expired,
#                     'allowed_modules': allowed_modules,
#                     'max_users': getattr(license_obj, 'max_users', 999),
#                     'license_key': getattr(license_obj, 'license_key', ''),
#                     'expiry_date': getattr(license_obj, 'expiry_date', None),
#                 }
                
#                 logger.info(
#                     f"[LICENSE INFO] License - Valid: {not is_expired}, "
#                     f"Expired: {is_expired}, Modules: {allowed_modules}"
#                 )
                
#             except LicenseKey.DoesNotExist:
#                 logger.warning(f"[LICENSE INFO] No active license for company {company_id}")
                
#         except Exception as e:
#             logger.error(f"[LICENSE INFO] Error loading license: {e}", exc_info=True)
        
#         return license_data
    
#     def _load_trial_data(self, company_id):
#         """Load trial data from Company model."""
#         trial_data = {
#             'trial_active': False,
#             'trial_expired': False,
#             'days_remaining': None,
#             'trial_message': '',
#             'trial_started_at': None,
#             'trial_expires_at': None,
#         }
        
#         try:
#             from company.models import Company
            
#             company = Company.objects.using('default').get(id=company_id)
            
#             # Check if trial is active
#             if not company.trial_active:
#                 logger.debug(f"[LICENSE INFO] Trial not active for company {company_id}")
#                 return trial_data
            
#             # Get trial summary using utility function
#             try:
#                 from company.utils.trial_utils import get_trial_summary
#                 trial_summary = get_trial_summary(company)
                
#                 trial_data = {
#                     'trial_active': company.trial_active,
#                     'trial_expired': trial_summary.get('is_expired', False),
#                     'days_remaining': trial_summary.get('days_remaining'),
#                     'trial_message': trial_summary.get('message', ''),
#                     'trial_started_at': company.trial_started_at,
#                     'trial_expires_at': company.trial_expires_at,
#                 }
                
#                 logger.info(
#                     f"[LICENSE INFO] Trial - Active: {company.trial_active}, "
#                     f"Expired: {trial_data['trial_expired']}, "
#                     f"Days: {trial_data['days_remaining']}"
#                 )
                
#             except ImportError:
#                 # Fallback if trial_utils not available
#                 logger.warning("[LICENSE INFO] trial_utils not available, using basic trial check")
#                 trial_data['trial_active'] = company.trial_active
                
#         except Exception as e:
#             logger.error(f"[LICENSE INFO] Error loading trial data: {e}", exc_info=True)
        
#         return trial_data
    
#     def _get_allowed_modules(self, license_obj):
#         """Extract allowed modules from LicenseKey object."""
#         try:
#             # Check module_access JSONField
#             if hasattr(license_obj, 'module_access') and license_obj.module_access:
#                 enabled_modules = [
#                     code for code, enabled in license_obj.module_access.items() 
#                     if enabled
#                 ]
#                 if enabled_modules:
#                     return enabled_modules
#                 return []
            
#             # Check license_key for special keywords
#             if hasattr(license_obj, 'license_key') and license_obj.license_key:
#                 license_key = license_obj.license_key.upper()
#                 if any(keyword in license_key for keyword in ['ALL', 'UNLIMITED', 'FULL', 'ENTERPRISE']):
#                     return None  # Full license
            
#             # Default: no modules
#             return []
            
#         except Exception as e:
#             logger.error(f"[LICENSE INFO] Error extracting modules: {e}")
#             return []


# class LicenseCheckMiddleware:
#     """
#     License and Trial Access Control Middleware
#     ==========================================
    
#     Purpose:
#     --------
#     Enforces license and trial restrictions by blocking access when appropriate.
    
#     Decision Flow:
#     -------------
#     1. First login (is_first_login=True) → Redirect to /company/setup/
#     2. Valid license (not expired) → Allow access
#     3. Trial active and not expired → Allow access
#     4. Trial expired and no license → Show trial_expired.html
#     5. No license and no trial → Show site_blocked.html
    
#     Execution Order:
#     ---------------
#     This MUST run AFTER LicenseInfoMiddleware which sets request.license_info
#     """
    
#     # URLs that don't need license enforcement
#     EXEMPT_PREFIXES = (
#         '/admin/',
#         '/static/',
#         '/media/',
#         '/login/',
#         '/logout/',
#         '/signup/',
#         '/Signup/',
#         '/company/license/',
#         '/company/create/',
#         '/company/update/',
#         '/company/ajax/',
#         '/bank/ajax/',
#         '/location/ajax/',
#         '/license/restricted/',
#         '/activate-license/',
#         '/trial-expired/',
#     )
    
#     def __init__(self, get_response):
#         """Initialize middleware."""
#         self.get_response = get_response
    
#     def __call__(self, request):
#         """Check license/trial and enforce access control."""
        
#         # ============================================
#         # STEP 1: Skip exempt URLs
#         # ============================================
#         if request.path.startswith(self.EXEMPT_PREFIXES):
#             logger.debug(f"[LICENSE CHECK] Exempt path: {request.path}")
#             return self.get_response(request)
        
#         # Skip company setup paths
#         if re.match(r'^/[A-Z0-9-]+/company/setup/', request.path) or request.path.startswith('/company/setup/'):
#             logger.debug(f"[LICENSE CHECK] Company setup path - allowing: {request.path}")
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 2: Skip unauthenticated users
#         # ============================================
#         if not request.user.is_authenticated:
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 3: Skip superusers
#         # ============================================
#         if request.user.is_superuser:
#             return self.get_response(request)
        
#         # ============================================
#         # STEP 4: Get license info from request
#         # ============================================
#         license_info = getattr(request, 'license_info', {})
        
#         is_first_login = license_info.get('is_first_login', True)
#         has_license = license_info.get('has_license', False)
#         is_valid = license_info.get('is_valid', False)
#         is_expired = license_info.get('is_expired', False)
#         trial_active = license_info.get('trial_active', False)
#         trial_expired = license_info.get('trial_expired', False)
#         allowed_modules = license_info.get('allowed_modules', [])
#         trial_expires_at = license_info.get('trial_expires_at')

#         # Determine if trial expiration can be inferred from expiry timestamp
#         expired_by_date = False
#         try:
#             if trial_expires_at:
#                 if isinstance(trial_expires_at, datetime):
#                     expired_by_date = date.today() > trial_expires_at.date()
#                 else:
#                     expired_by_date = date.today() > trial_expires_at
#         except Exception:
#             expired_by_date = False
        
#         logger.debug(
#             f"[LICENSE CHECK] User: {request.user.username}, "
#             f"First Login: {is_first_login}, "
#             f"Has License: {has_license}, "
#             f"Valid: {is_valid}, "
#             f"Trial: {trial_active}/{trial_expired}"
#         )
        
#         # ============================================
#         # DECISION LOGIC
#         # ============================================
        
#         # ❌ PRIORITY 1: FIRST LOGIN - Redirect to setup
#         if is_first_login:
#             if not (request.path.startswith('/company/setup/') or 
#                     re.match(r'^/[A-Z0-9-]+/company/setup/', request.path)):
#                 logger.warning(
#                     f"[LICENSE CHECK] 🚨 FIRST LOGIN - Redirecting to company setup"
#                 )
#                 company_code = getattr(request, 'company_code', None)
#                 if company_code:
#                     return redirect(f'/{company_code}/company/setup/')
#                 return redirect('/company/setup/')
#             # Already on setup page
#             return self.get_response(request)
        
#         # ✅ PRIORITY 2: VALID LICENSE - Allow access
#         if has_license and is_valid and not is_expired:
#             if allowed_modules is None or allowed_modules:
#                 logger.info(f"[LICENSE CHECK] ✅ ALLOW - Valid license")
#                 return self.get_response(request)
#             else:
#                 logger.warning(f"[LICENSE CHECK] ❌ BLOCK - No modules")
#                 return redirect('/license/restricted/')
        
#         # ✅ PRIORITY 3: TRIAL ACTIVE - Allow access
#         if trial_active and not trial_expired:
#             logger.info(f"[LICENSE CHECK] ✅ ALLOW - Trial active")
#             return self.get_response(request)

#         # ❌ PRIORITY 4: TRIAL EXPIRED - Show trial expired page
#         # Also handle case where there is NO license and trial expiry date is past
#         if (trial_active and trial_expired) or (not has_license and (trial_expired or expired_by_date)):
#             logger.warning(f"[LICENSE CHECK] ❌ BLOCK - Trial expired")
#             return self._render_trial_expired(request, license_info)
        
#         # ❌ PRIORITY 5: NO LICENSE, NO TRIAL - Show site blocked
#         logger.warning(f"[LICENSE CHECK] ❌ BLOCK - No valid license or trial")
#         return redirect('/license/restricted/')
    
#     def _render_trial_expired(self, request, license_info):
#         """Render trial expired page."""
#         company_id = getattr(request, 'company_id', None)
#         company_code = getattr(request, 'company_code', None)
        
#         context = {
#             'company_id': company_id,
#             'company_code': company_code,
#             'license_info': license_info,
#             'contact_email': 'support@lyraerp.com',
#         }
        
#         return render(request, 'trial_expired.html', context, status=403)


# # ============================================
# # END OF MIDDLEWARE
# # ============================================



"""
License and Trial Middleware - COMPLETE INTEGRATED VERSION
===========================================================

FIXED: Redirect loop on /license/restricted/ caused by company-code-prefixed URLs
       not matching the EXEMPT_PREFIXES list. Now uses fragment matching.

VERSION: 5.1 - Fixed redirect loop
"""
import logging
import re
from datetime import date, datetime
from django.shortcuts import redirect, render
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.urls import reverse

logger = logging.getLogger(__name__)


# ============================================================================
# SHARED EXEMPT FRAGMENTS
# These work with company-code-prefixed URLs like /KTKIMPEX-2026-9S9Y/license/restricted/
# ============================================================================

# startswith() exempt — paths that never have a company code prefix
EXEMPT_PREFIXES = (
    '/admin/',
    '/static/',
    '/media/',
    '/login/',
    '/logout/',
    '/signup/',
    '/Signup/',
)

# fragment exempt — paths that MAY be prefixed with a company code
# Checked with:  any(fragment in request.path for fragment in EXEMPT_FRAGMENTS)
EXEMPT_FRAGMENTS = (
    '/admin/',
    'license/restricted',
    'activate-license',
    'user/profile',
    'user/edit',
    'user/user/',
    'user/change_password',
    'user/delete',
    'trial-expired',
    'activity/new_logs/',
    'company/license/',
    'company/create/',
    'company/update/',
    'company/ajax/',
    'bank/ajax/',
    'location/ajax/',
    'company/setup/',
    
)


def _is_exempt(path):
    """
    Return True if the given path should skip license enforcement.
    Handles both plain paths (/license/restricted/) and
    company-code-prefixed paths (/KTKIMPEX-2026-9S9Y/license/restricted/).
    """
    # First check prefix exempts
    if path.startswith(EXEMPT_PREFIXES):
        logger.debug(f"[EXEMPT CHECK] ✅ Path '{path}' matches EXEMPT_PREFIXES")
        return True
    
    # Then check fragment exempts
    for fragment in EXEMPT_FRAGMENTS:
        if fragment in path:
            logger.debug(
                f"[EXEMPT CHECK] ✅ Path '{path}' contains fragment '{fragment}'"
            )
            return True
    
    logger.debug(
        f"[EXEMPT CHECK] ❌ Path '{path}' is NOT exempt. "
        f"(Prefixes: {EXEMPT_PREFIXES}, Fragments: {EXEMPT_FRAGMENTS})"
    )
    return False


# ============================================================================
# LicenseInfoMiddleware
# ============================================================================

class LicenseInfoMiddleware:
    """
    Loads license and trial information into every request.
    Does NOT block access — only loads information.
    Must run AFTER CompanyDBMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Quick explicit allow for user profile (ensure accessible to authenticated users)
        if '/user/profile' in request.path:
            logger.debug("[LICENSE CHECK] Explicit allow for user profile path: %s", request.path)
            return self.get_response(request)

        # ── Default license info ────────────────────────────────────────────
        request.license_info = {
            'has_license':      False,
            'is_valid':         False,
            'is_expired':       False,
            'allowed_modules':  [],
            'max_users':        0,
            'license_key':      '',
            'expiry_date':      None,
            'license_type':     'none',
            'allowed_modules':  None,
            'trial_active':     False,
            'trial_expired':    False,
            'days_remaining':   None,
            'trial_message':    '',
            'trial_started_at': None,
            'trial_expires_at': None,
            'setup_complete':   False,
            'is_first_login':   True,
        }

        # ── Exempt paths ────────────────────────────────────────────────────
        if _is_exempt(request.path):
            logger.debug("[LICENSE INFO] Exempt path: %s", request.path)
            return self.get_response(request)

        # ── Unauthenticated ─────────────────────────────────────────────────
        if not request.user.is_authenticated:
            return self.get_response(request)

        # ── Superuser — full access ─────────────────────────────────────────
        if request.user.is_superuser:
            request.license_info.update({
                'has_license':     True,
                'is_valid':        True,
                'is_expired':      False,
                'allowed_modules': None,   # None = ALL modules
                'max_users':       999,
                'license_key':     'SUPERUSER',
                'license_type':    'superuser',
                'setup_complete':  True,
                'is_first_login':  False,
            })
            return self.get_response(request)

        # ── Company info ────────────────────────────────────────────────────
        company_db = getattr(request, 'company_db', 'default')
        company_id = getattr(request, 'company_id', None)

        logger.debug(f"[MIDDLEWARE-INIT] company_db='{company_db}', company_id={company_id}")

        if not company_id:
            return self.get_response(request)

        # ── Setup / first-login ─────────────────────────────────────────────
        request.license_info['setup_complete'] = self._check_setup_complete(company_id)
        request.license_info['is_first_login'] = self._is_first_login(company_id)

        # ── License & trial data ────────────────────────────────────────────
        license_data = self._load_license_data(company_db, company_id)
        trial_data   = self._load_trial_data(company_id)

        request.license_info.update(license_data)
        request.license_info.update(trial_data)

        # ── Overall validity ────────────────────────────────────────────────
        has_valid_license   = license_data.get('is_valid', False) and not license_data.get('is_expired', True)
        trial_active_valid  = trial_data.get('trial_active', False) and not trial_data.get('trial_expired', True)

        # A company is valid if EITHER they have a valid license OR an active trial.
        # CRITICAL: A valid license ALWAYS takes precedence over trial expiration.
        request.license_info['is_valid'] = has_valid_license or trial_active_valid
        
        request.license_info['license_type'] = (
            'licensed' if has_valid_license else
            'trial'    if trial_active_valid else
            'none'
        )
        
        if trial_active_valid and not has_valid_license:
            request.license_info['allowed_modules'] = None  # Trial gives access to all modules

        logger.info(
            "[LICENSE INFO] company_id=%s db=%s type=%s valid=%s license=%s/%s trial=%s/%s",
            company_id,
            company_db,
            request.license_info['license_type'],
            request.license_info['is_valid'],
            license_data.get('has_license'),
            license_data.get('is_expired'),
            trial_data.get('trial_active'),
            trial_data.get('trial_expired'),
        )


        return self.get_response(request)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _check_setup_complete(self, company_id):
        try:
            from company.models import Company
            return Company.objects.using('default').get(id=company_id).setup_complete
        except Exception as e:
            logger.error("[LICENSE INFO] Error checking setup: %s", e)
            return False

    def _is_first_login(self, company_id):
        try:
            from company.models import Company
            company = Company.objects.using('default').get(id=company_id)
            return not bool(company.first_login_completed)
        except Exception as e:
            logger.error("[LICENSE INFO] Error checking first login: %s", e)
            return True

    def _load_license_data(self, company_db, company_id):
        data = {
            'has_license':     False,
            'is_valid':        False,
            'is_expired':      False,
            'allowed_modules': [],
            'max_users':       0,
            'license_key':     '',
            'expiry_date':     None,
        }
        try:
            from company_settings.models import LicenseKey

            try:
                license_obj = LicenseKey.objects.using(company_db).get(
                    company_id=company_id,
                    is_active=True,
                )
                
                logger.debug(f"[MIDDLEWARE-LICENSE] ✅ Found license in DB '{company_db}': key={license_obj.license_key[:15]}...")

                # ── expiry check (support attribute flag or method) ───────────
                is_expired = False
                if hasattr(license_obj, 'is_license_expired'):
                    try:
                        is_expired = bool(license_obj.is_license_expired)
                        logger.debug(f"[MIDDLEWARE-LICENSE] Using is_license_expired flag: {is_expired}")
                    except Exception:
                        is_expired = False
                elif hasattr(license_obj, 'is_expired') and callable(getattr(license_obj, 'is_expired')):
                    try:
                        is_expired = bool(license_obj.is_expired())
                        logger.debug(f"[MIDDLEWARE-LICENSE] Using is_expired() method: {is_expired}")
                    except Exception:
                        is_expired = False
                elif hasattr(license_obj, 'expiry_date') and license_obj.expiry_date:
                    try:
                        is_expired = date.today() > license_obj.expiry_date
                        logger.debug(f"[MIDDLEWARE-LICENSE] Using expiry_date comparison: {is_expired}")
                    except Exception:
                        is_expired = False

                allowed_modules = self._get_allowed_modules(license_obj)

                data = {
                    'has_license':     True,
                    'is_valid':        not is_expired,
                    'is_expired':      is_expired,
                    'allowed_modules': allowed_modules,
                    'max_users':       getattr(license_obj, 'max_users', 999),
                    'license_key':     getattr(license_obj, 'license_key', ''),
                    'expiry_date':     getattr(license_obj, 'expiry_date', None),
                }

                logger.debug(f"[MIDDLEWARE-LICENSE] Result: has_license=True, is_valid={not is_expired}, is_expired={is_expired}, allowed_modules={allowed_modules}")

                logger.info(
                    "[LICENSE INFO] License valid=%s expired=%s (flag=%s) modules=%s",
                    not is_expired, is_expired, getattr(license_obj, 'is_license_expired', None), allowed_modules,
                )

            except LicenseKey.DoesNotExist:
                logger.debug(f"[MIDDLEWARE-LICENSE] ❌ No active license found in DB '{company_db}' for company_id={company_id}")
                logger.warning("[LICENSE INFO] No active license for company %s in DB %s", company_id, company_db)

        except Exception as e:
            logger.debug(f"[MIDDLEWARE-LICENSE] ERROR: {e}")
            logger.error("[LICENSE INFO] Error loading license: %s", e, exc_info=True)

        return data

    def _load_trial_data(self, company_id):
        data = {
            'trial_active':     False,
            'trial_expired':    False,
            'days_remaining':   None,
            'trial_message':    '',
            'trial_started_at': None,
            'trial_expires_at': None,
        }
        try:
            from company.models import Company
            company = Company.objects.using('default').get(id=company_id)

            # ── CRITICAL: Always check is_trial_expired flag, even if trial_active=False ──
            # Reason: Trial can expire while inactive (was active in past, then expired)
            # This flag determines if license-expired page should be shown
            is_trial_expired = bool(company.is_trial_expired)
            
            # If trial is EXPIRED, flag it regardless of trial_active status
            # This ensures "License Expired + Trial Ended" scenario shows correct page
            if is_trial_expired:
                data['trial_expired'] = True
                days_remaining = company.days_until_trial_expires()
                data['days_remaining'] = days_remaining
                data['trial_message'] = (
                    f'Trial expired {abs(days_remaining) if days_remaining else 0} days ago' 
                    if days_remaining and days_remaining < 0 
                    else 'Trial expired'
                )
                logger.info(
                    "[LICENSE INFO] Trial EXPIRED (flag=%s) even though trial_active=%s — days=%s",
                    is_trial_expired, company.trial_active, days_remaining,
                )
                return data  # Return early with trial_expired=True
            
            # If trial is not expired but not active, return defaults
            if not company.trial_active:
                return data

            # ── Trial is ACTIVE and NOT EXPIRED ──
            # Calculate days remaining for display
            days_remaining = company.days_until_trial_expires()
            
            # Build status message
            trial_message = ''
            if days_remaining == 0:
                trial_message = 'Trial expires today'
            elif days_remaining is not None and days_remaining <= 5:
                trial_message = f'{days_remaining} days remaining'
            else:
                trial_message = f'{days_remaining} days remaining' if days_remaining else ''
            
            data = {
                'trial_active':     True,
                'trial_expired':    False,
                'days_remaining':   days_remaining,
                'trial_message':    trial_message,
                'trial_started_at': company.trial_started_at,
                'trial_expires_at': company.trial_expires_at,
            }
            
            logger.info(
                "[LICENSE INFO] Trial ACTIVE and NOT expired — days=%s",
                days_remaining,
            )

        except Exception as e:
            logger.error("[LICENSE INFO] Error loading trial: %s", e, exc_info=True)

        return data

    def _get_allowed_modules(self, license_obj):
        try:
            if hasattr(license_obj, 'module_access') and license_obj.module_access:
                enabled = [k for k, v in license_obj.module_access.items() if v]
                return enabled if enabled else []
            if hasattr(license_obj, 'license_key'):
                key = license_obj.license_key.upper()
                if any(kw in key for kw in ['ALL', 'UNLIMITED', 'FULL', 'ENTERPRISE']):
                    return None
            return []
        except Exception as e:
            logger.error("[LICENSE INFO] Error extracting modules: %s", e)
            return []


# ============================================================================
# LicenseCheckMiddleware
# ============================================================================

class LicenseCheckMiddleware:
    """
    Enforces license/trial restrictions.
    Must run AFTER LicenseInfoMiddleware.

    FIXED: Uses _is_exempt() which handles company-code-prefixed URLs,
           preventing the redirect loop on /COMPANY/license/restricted/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Quick explicit allow for user profile (ensure accessible to authenticated users)
        if '/user/profile' in request.path:
            logger.debug("[LICENSE CHECK] Explicit allow for user profile path: %s", request.path)
            return self.get_response(request)

        # ── Exempt ──────────────────────────────────────────────────────────
        exempt = _is_exempt(request.path)
        logger.debug(
            "[LICENSE CHECK] Checking path: '%s' — exempt=%s",
            request.path, exempt
        )
        if exempt:
            logger.debug("[LICENSE CHECK] ✅ Path is EXEMPT — allowing access")
            return self.get_response(request)

        # ── Unauthenticated ─────────────────────────────────────────────────
        if not request.user.is_authenticated:
            return self.get_response(request)

        # ── Superuser ────────────────────────────────────────────────────────
        if request.user.is_superuser:
            return self.get_response(request)

        # ── Read license info ────────────────────────────────────────────────
        info = getattr(request, 'license_info', {})

        is_first_login   = info.get('is_first_login', True)
        has_license      = info.get('has_license', False)
        is_valid         = info.get('is_valid', False)
        is_expired       = info.get('is_expired', False)
        trial_active     = info.get('trial_active', False)
        trial_expired    = info.get('trial_expired', False)
        allowed_modules  = info.get('allowed_modules', [])

        logger.debug(
            "[LICENSE CHECK] user=%s first=%s license=%s valid=%s trial=%s/%s",
            request.user.username, is_first_login,
            has_license, is_valid, trial_active, trial_expired,
        )

        # ── Decision tree ────────────────────────────────────────────────────

        # 1. First login → company setup
        if is_first_login:
            if not ('company/setup/' in request.path):
                logger.warning("[LICENSE CHECK] First login — redirecting to setup")
                # Use named URL for company setup to allow redirect_utils to build proper path
                try:
                    return redirect_with_company(request, 'company_registration')
                except Exception:
                    # Fallback to direct path if reversal fails
                    company_code = getattr(request, 'company_code', None)
                    if company_code:
                        return redirect(f'/{company_code}/company/setup/')
                    return redirect('/company/setup/')
            return self.get_response(request)

        # 2. Valid license → allow
        if has_license and is_valid and not is_expired:
            if allowed_modules is None or allowed_modules:
                logger.debug("[LICENSE CHECK] ✅ Valid license — allow")
                return self.get_response(request)
            else:
                logger.warning("[LICENSE CHECK] ❌ No modules in license")
                return self._redirect_restricted(request)

        # 2.5 Expired license → if trial also ended, show license-expired page;
        # otherwise treat as restricted (site_blocked)
        if has_license and is_expired:
            if trial_expired:
                logger.warning("[LICENSE CHECK] ❌ License expired and trial ended — show license expired page")
                return self._render_license_expired(request, info)
            logger.warning("[LICENSE CHECK] ❌ License present but expired — restricted")
            return self._redirect_restricted(request)

        # 3. Active trial → allow
        if trial_active and not trial_expired:
            logger.debug("[LICENSE CHECK] ✅ Trial active — allow")
            return self.get_response(request)

        # 4. Trial expired → trial expired page
        # Only block here if there is NO valid license found.
        if trial_expired and not has_license:
            logger.warning("[LICENSE CHECK] ❌ Trial expired and no license found - license_info=%s", info)
            return self._render_trial_expired(request, info)


        # 5. No license, no trial → restricted
        logger.warning("[LICENSE CHECK] ❌ No valid license or trial")
        return self._redirect_restricted(request)

    def _redirect_restricted(self, request):
        """Redirect to the license restricted page with company code prefix."""
        company_code = getattr(request, 'company_code', None)
        # Prefer reversing the named URL `license_restricted` so redirect_utils
        # can insert the company_code correctly. Fall back to path if needed.
        try:
            return redirect_with_company(request, 'license_restricted')
        except Exception:
            if company_code:
                return redirect(f'/{company_code}/license/restricted/')
            return redirect('/license/restricted/')

    def _render_trial_expired(self, request, license_info):
        # Redirect to a dedicated URL so the browser location clearly indicates
        # trial-expired state instead of returning 403 on the originally requested path.
        try:
            return redirect_with_company(request, 'trial_expired_page')
        except Exception:
            company_code = getattr(request, 'company_code', None)
            if company_code:
                return redirect(f'/{company_code}/trial-expired/')
            return self._redirect_restricted(request)

    def _render_license_expired(self, request, license_info):
        """Render the license expired page (license was activated but is now expired)."""
        context = {
            'company_id':    getattr(request, 'company_id', None),
            'company_code':  getattr(request, 'company_code', None),
            'license_info':  license_info,
            'contact_email': 'mailmaster@techlyra.com',
        }
        # Use the company license_expired template
        return render(request, 'company/license_expired.html', context, status=403)
