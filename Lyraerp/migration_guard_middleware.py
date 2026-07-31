"""
migration_guard_middleware.py
=============================
Shows the company setup page (which has its own built-in migration progress UI)
when a user navigates to an app page (sales, HR, purchases etc.) while the
company DB is still being set up.

CHANGE: migration_progress.html has been removed. Instead of rendering that
standalone template, the middleware now redirects the user back to the company
setup page (/COMPANY_CODE/company/setup/) which already contains a fully
featured migration progress UI (spinner, stage track, progress bar, poller).
This means migration_progress.html can be safely deleted.

WHAT IT GUARDS
--------------
- Any company-URL page that queries the company DB  e.g. /XYZ/sales/...
- NOT /XYZ/company/setup/ — that page IS the setup flow itself
- NOT /XYZ/company/...    — registration / setup sub-pages
- NOT static, media, auth, api paths

SOURCE OF TRUTH
---------------
Asks MySQL directly: "does sales_salesquotation exist in this DB?"
No dependency on any in-memory status dict or external module.
Result cached in-process once True; never cached while False.

SETUP
-----
1. settings.py MIDDLEWARE — place right after CompanyCodeMiddleware:
       'Lyraerp.migration_guard_middleware.MigrationGuardMiddleware',

2. root urls.py:
       path('_migration_status/', include('Lyraerp.migration_status_urls')),
       path('<str:company_code>/_migration_status/', include('Lyraerp.migration_status_urls')),

3. migration_progress.html is NO LONGER NEEDED and can be deleted.
"""

import re
import importlib
import logging
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Paths that ALWAYS bypass the guard (no company DB needed)
# ---------------------------------------------------------------------------
_ALWAYS_ALLOW_PREFIXES = (
    '/static/',
    '/media/',
    '/admin/',
    '/login/',
    '/logout/',
    '/signup/',
    '/Signup/',
    '/check-email/',
    '/check-username/',
    '/api/',
    '/_migration_status/',
)

# ---------------------------------------------------------------------------
# 2. Path SEGMENTS (after the company code) that bypass the guard.
#    These are pages that either run during setup or don't need app tables.
#    We also allow the *empty* second segment (company root / dashboard) so
#    the user can land on their dashboard while migrations continue in the
#    background. Clicking a real module link will still trigger the guard.
# ---------------------------------------------------------------------------
_EXEMPT_SECOND_SEGMENTS = {
    'company',              # /XYZ/company/setup/, /XYZ/company/... — setup flow itself
    'user',                 # /XYZ/user/... — user management, may run early
    '_migration_status',    # /XYZ/_migration_status/ — polling endpoint
    '',                     # root path after the company code; show dashboard even if
                            # migrations are pending
}

# Matches /ABC1UHZ7L1LZ/anything
_COMPANY_CODE_RE = re.compile(r'^/([A-Z0-9][A-Z0-9\-]{2,})/([^/]*)')
_ADMIN_PATH_RE = re.compile(r'^/(?:[A-Z0-9-]+/)?admin(?:/|$)')

# Cache: company_code → db_name string  ('' = not found/not created yet)
_DB_NAME_CACHE: dict = {}

# Cache: db_name → True once confirmed ready (never stores False)
_DB_READY_CACHE: set = set()

# The sentinel table — created near the END of migrations.
# When this exists, the DB is fully migrated.
_SENTINEL_TABLE = 'sales_salesquotation'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_always_allowed(path: str) -> bool:
    return bool(_ADMIN_PATH_RE.match(path or '')) or any(path.startswith(p) for p in _ALWAYS_ALLOW_PREFIXES)


def _get_db_name(company_code: str):
    """Return db_name for company_code, or None. Cached after first lookup."""
    if company_code in _DB_NAME_CACHE:
        return _DB_NAME_CACHE[company_code] or None

    try:
        from company.models import Company
        row = Company.objects.using('default').filter(
            company_code=company_code
        ).values('db_name', 'db_created').first()

        if row and row['db_created'] and row['db_name']:
            _DB_NAME_CACHE[company_code] = row['db_name']
            return row['db_name']

        _DB_NAME_CACHE[company_code] = ''
        return None

    except Exception as exc:
        logger.debug("MigrationGuard: DB lookup failed for %s: %s", company_code, exc)
        return None


def _ensure_db_registered(db_name: str):
    """Make sure db_name is in Django DATABASES so we can open a connection."""
    from django.conf import settings
    if db_name not in settings.DATABASES:
        try:
            from Lyraerp.utils.db_utils import register_database
            register_database(db_name)
        except Exception:
            default = settings.DATABASES['default']
            settings.DATABASES[db_name] = {
                'ENGINE':   default['ENGINE'],
                'NAME':     db_name,
                'USER':     default.get('USER', ''),
                'PASSWORD': default.get('PASSWORD', ''),
                'HOST':     default.get('HOST', 'localhost'),
                'PORT':     default.get('PORT', '3306'),
            }


def _is_db_ready(db_name: str) -> bool:
    """
    True if the sentinel table exists → migrations are complete.
    False otherwise. True result is cached permanently; False is never cached.
    """
    if db_name in _DB_READY_CACHE:
        return True

    try:
        _ensure_db_registered(db_name)
        from django.db import connections
        with connections[db_name].cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s",
                [db_name, _SENTINEL_TABLE]
            )
            exists = cursor.fetchone()[0] > 0

        if exists:
            _DB_READY_CACHE.add(db_name)
            logger.info("MigrationGuard: DB %s is ready", db_name)
        else:
            logger.debug("MigrationGuard: DB %s not ready yet", db_name)

        return exists

    except Exception as exc:
        logger.debug("MigrationGuard: cannot check DB %s: %s", db_name, exc)
        return False


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MigrationGuardMiddleware:
    """
    Redirects to the company setup page when a user hits an app URL while
    the company DB is still being created.

    The setup page (/COMPANY_CODE/company/setup/) already contains a full
    migration progress UI (spinner, stage track, progress bar, JSON poller)
    so no separate migration_progress.html template is needed.

    Exempts the company setup flow itself so registration is never blocked.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 1. Always-exempt paths (static, auth, api…)
        if _is_always_allowed(path):
            return self.get_response(request)

        # 2. Must match /COMPANYCODE/segment/...
        match = _COMPANY_CODE_RE.match(path)
        if not match:
            return self.get_response(request)

        company_code   = match.group(1)
        second_segment = match.group(2).lower()

        # 3. Exempt setup/registration URLs and the migration status poll endpoint.
        if second_segment in _EXEMPT_SECOND_SEGMENTS:
            return self.get_response(request)

        # 4. Get the company DB name
        db_name = _get_db_name(company_code)
        if not db_name:
            return self.get_response(request)

        # 5. If DB is fully migrated, let the view run normally
        if _is_db_ready(db_name):
            return self.get_response(request)

        # 6. DB not ready — redirect to the company setup page.
        #    The setup page has a built-in migration progress UI that polls
        #    /_migration_status/?db=<db_name> and auto-redirects once done.
        setup_url = f'/{company_code}/company/setup/'
        logger.info(
            "MigrationGuard: intercepted %s (company=%s db=%s) — DB not ready, "
            "redirecting to setup page %s",
            path, company_code, db_name, setup_url,
        )
        return HttpResponseRedirect(setup_url)
