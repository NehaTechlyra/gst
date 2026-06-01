"""
migration_status_view.py
------------------------
JSON polling endpoint for the migration progress page.

GET /_migration_status/?db=lyra_efg1_26
GET /<company_code>/_migration_status/?db=lyra_efg1_26   ← also supported now

→ {"status": "running", "progress": "3/7: Configuring modules...", "error": null}

Sentinel table presence alone is not treated as completion. We only return
{"status": "completed"} when async setup status explicitly says completed.

✅ FIX: Added company_code=None parameter so Django doesn't raise TypeError
        when this view is called via the /<company_code>/_migration_status/ route.
✅ FIX: Added Content-Type: application/json header explicitly so the frontend
        can reliably detect JSON vs HTML error pages.
✅ FIX: Ensure db is registered before querying so first poll never fails silently.
"""
import re
import importlib
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

_SAFE_DB_RE     = re.compile(r'^[a-zA-Z0-9_\-]+$')
_SENTINEL_TABLE = 'sales_salesquotation'


def _table_exists(db_name: str) -> bool:
    """
    Check via information_schema whether the sentinel table exists.

    Also registers the database with Django if necessary so the
    `connections` dictionary can open a cursor for it.
    """
    try:
        from django.db import connections
        from django.conf import settings

        # ✅ ensure the database is known to Django before connecting
        if db_name not in settings.DATABASES:
            try:
                from Lyraerp.utils.db_utils import register_database
                register_database(db_name)
                logger.debug("migration_status: registered db %s via db_utils", db_name)
            except Exception:
                # Fallback: clone connection params from default
                default = settings.DATABASES['default']
                settings.DATABASES[db_name] = {
                    'ENGINE':   default['ENGINE'],
                    'NAME':     db_name,
                    'USER':     default.get('USER', ''),
                    'PASSWORD': default.get('PASSWORD', ''),
                    'HOST':     default.get('HOST', 'localhost'),
                    'PORT':     default.get('PORT', '3306'),
                }
                logger.debug("migration_status: registered db %s via fallback clone", db_name)

        with connections[db_name].cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s",
                [db_name, _SENTINEL_TABLE]
            )
            return cursor.fetchone()[0] > 0

    except Exception as exc:
        logger.debug("migration_status: table check failed for %s: %s", db_name, exc)
        return False


def _get_status_from_dict(db_name: str):
    """Try every known location for MIGRATION_STATUS. Returns dict or None."""
    for module_path in (
        'Lyraerp.async_migrations',
        'async_migrations',
        'Lyraerp.utils.async_migrations',
    ):
        try:
            mod = importlib.import_module(module_path)
            status_dict = getattr(mod, 'MIGRATION_STATUS', {})
            if db_name in status_dict:
                return status_dict[db_name]
            return None   # module found, no entry for this DB
        except ImportError:
            continue
        except Exception:
            return None
    return None


# ✅ FIX: Accept optional company_code so this view works on BOTH URL patterns:
#   /_migration_status/?db=...
#   /<company_code>/_migration_status/?db=...
@csrf_exempt
@require_GET
def migration_status(request, company_code=None):
    db_name = request.GET.get('db', '').strip()

    if not db_name:
        return JsonResponse(
            {'error': 'db parameter required'},
            status=400,
            content_type='application/json',
        )

    if not _SAFE_DB_RE.match(db_name):
        return JsonResponse(
            {'error': 'invalid db name'},
            status=400,
            content_type='application/json',
        )

    logger.debug("migration_status: polling db=%s (company_code=%s)", db_name, company_code)

    table_ready = _table_exists(db_name)

    # Try to get a human-readable progress message
    info = _get_status_from_dict(db_name)

    # If async logic already marked this DB completed, honour it immediately
    if info and info.get('status') == 'completed':
        return JsonResponse(
            {
                'db':       db_name,
                'status':   'completed',
                'progress': info.get('progress', 'Setup completed'),
                'error':    info.get('error'),
                'stage':    info.get('stage', 'setup'),
            },
            content_type='application/json',
        )

    if info:
        return JsonResponse(
            {
                'db':       db_name,
                'status':   info.get('status', 'running'),
                'progress': info.get('progress', 'Setting up your database…'),
                'error':    info.get('error'),
                'stage':    info.get('stage', 'setup'),
            },
            content_type='application/json',
        )

    # Table may exist while post-migration setup still runs; do not mark completed
    # until async status explicitly reports completion.
    if table_ready:
        return JsonResponse(
            {
                'db':       db_name,
                'status':   'running',
                'progress': 'Migrations finished, finalizing setup…',
                'error':    None,
                'stage':    'setup',
            },
            content_type='application/json',
        )

    # No status dict entry — still setting up, no detail available yet
    return JsonResponse(
        {
            'db':       db_name,
            'status':   'running',
            'progress': 'Setting up your database, please wait…',
            'error':    None,
            'stage':    'setup',
        },
        content_type='application/json',
    )
