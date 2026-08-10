"""
================
Shared utilities for the company app.

License-activation helpers live here so that BOTH the first-time
registration flow  (registration_views.py)  and the post-login
company-setup flow (views.py / save_license_configuration)
hit the exact same code-path: validate → save → confirm.

Public API
----------
activate_license_for_company(company, license_key, request)
    Full three-phase activation.  Returns a plain dict:
        {"success": True,  "license": <LicenseKey instance>, "message": …}
    or  {"success": False, "message": …}

build_license_response(license_obj)
    Serialise a LicenseKey instance into the JSON-ready dict that both
    views return to the front-end.

validate_with_generator(license_key, company_id, company_name,
                        company_gst, erp_version)
    Phase 1 – POST to the external generator API.  Returns
    {"success": True, "license": <dict from generator>}
    or  {"success": False, "message": …}

confirm_with_generator(license_key, company_id, company_name,
                       company_gst)
    Phase 3 – fire-and-forget confirmation POST.  Swallows errors
    intentionally (the ERP has already persisted the license).

get_client_ip(request)
    Pull the real client IP, honouring X-Forwarded-For.

generate_license_key(company_id)
    Create a one-off license-key string (used during *generation*,
    not activation).

get_default_module_access()
    Return the baseline {module_code: False} map from SYSTEM_MODULES.

license_required(module_code)
    View decorator that gates access on an active license + module flag.
"""

import uuid
import hashlib
import logging
import base64
import os
from datetime import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib import messages

from company.erp_config import ERP_VERSION
from company.constants import SYSTEM_MODULES
# LicenseKey is imported lazily inside functions to avoid circular imports
# at module-load time.  The model lives in company_settings.models.

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IP extraction
# ---------------------------------------------------------------------------

def get_client_ip(request):
    """Return the client's IP address, honouring X-Forwarded-For."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_company_logo_base64(company):
    """
    Return a base64-encoded representation of the company's logo.
    Falls back to reading the logo file if the cached `logo_base64` field is empty.
    """
    if not company:
        return ""
    existing = getattr(company, 'logo_base64', None)
    if existing:
        return existing

    logo_field = getattr(company, 'logo', None)
    if not logo_field:
        return ""

    try:
        with logo_field.open('rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        pass

    path = getattr(logo_field, 'path', None)
    if path and os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            pass

    return ""
# ---------------------------------------------------------------------------
# Generator API helpers  (Phase 1 & Phase 3)
# ---------------------------------------------------------------------------

def validate_with_generator(license_key, company_id, company_name,
                            company_gst, erp_version):
    """
    Phase 1 – validate a license key against the external generator.
    
    ENHANCED VERSION with detailed diagnostics for 404 errors.
    """
    
    # Log the exact request we're about to make
    logger.info("=" * 80)
    logger.info("[VALIDATE_GENERATOR] Starting validation")
    logger.info("=" * 80)
    logger.info(f"Generator URL: {settings.LICENSE_GENERATOR_API_URL}")
    logger.info(f"License Key: '{license_key}'")
    logger.info(f"  - Length: {len(license_key)}")
    logger.info(f"  - Has dashes: {'-' in license_key}")
    logger.info(f"  - Format: {'XXXX-XXXX-XXXX-XXXX' if len(license_key.split('-')) == 4 else 'Unknown'}")
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Company Name: '{company_name}'")
    logger.info(f"Company GST: '{company_gst}'")
    logger.info(f"ERP Version: {erp_version}")
    
    payload = {
        'license_key': license_key,
        'company_id': company_id,
        'company_name': company_name,
        'company_gst': company_gst,
        'erp_version': erp_version,
        'erp_confirmed': False,
    }
    
    logger.info("\nRequest Payload:")
    import json
    logger.info(json.dumps(payload, indent=2))
    logger.info("=" * 80)
    
    try:
        endpoint = f"{settings.LICENSE_GENERATOR_API_URL}/api/activate/"
        logger.info(f"POST {endpoint}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        
        # Handle different status codes
        if response.status_code == 404:
            logger.error("❌ Generator returned 404 - License Not Found")
            logger.error("This means the license key does not exist in the generator database")
            logger.error("\nPossible causes:")
            logger.error("1. License key format mismatch (check dashes, case sensitivity)")
            logger.error("2. License not generated yet in the generator system")
            logger.error("3. License was deleted from generator database")
            logger.error("4. Generator API endpoint is wrong")
            logger.error("\nDebugging steps:")
            logger.error(f"1. Check generator database for: '{license_key}'")
            logger.error(f"2. Try without dashes: '{license_key.replace('-', '')}'")
            logger.error(f"3. Check generator logs for this request")
            logger.error(f"4. Verify generator API is running at: {settings.LICENSE_GENERATOR_API_URL}")
            
            # Try to get response body for more info
            try:
                error_data = response.json()
                logger.error(f"\nGenerator error response: {json.dumps(error_data, indent=2)}")
                return {
                    'success': False,
                    'message': error_data.get('message', 'License key not found in generator database'),
                }
            except:
                logger.error(f"\nRaw response: {response.text[:500]}")
                
            return {
                'success': False,
                'message': (
                    f'License key "{license_key}" not found in generator database. '
                    'Please verify the license key is correct and has been generated. '
                    'Contact your vendor if this issue persists.'
                ),
            }
        
        if response.status_code == 400:
            logger.error("❌ Generator returned 400 - Bad Request")
            try:
                error_data = response.json()
                logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                return {
                    'success': False,
                    'message': error_data.get('message', 'Invalid request to license generator'),
                }
            except:
                logger.error(f"Raw response: {response.text[:500]}")
                return {
                    'success': False,
                    'message': 'Invalid request to license generator',
                }
        
        if response.status_code == 500:
            logger.error("❌ Generator returned 500 - Server Error")
            return {
                'success': False,
                'message': 'License generator server error. Please try again later or contact support.',
            }
        
        if response.status_code != 200:
            logger.warning(
                "[validate_with_generator] Generator returned %s for key=%s",
                response.status_code, license_key,
            )
            return {
                'success': False,
                'message': 'License server unavailable. Please contact support.',
            }
        
        # Success - parse response
        data = response.json()
        logger.info("✅ Generator response received")
        logger.info(f"Success: {data.get('success')}")
        
        if not data.get('success'):
            logger.error(f"❌ Generator validation failed: {data.get('message')}")
            return {
                'success': False,
                'message': data.get('message', 'License validation failed'),
            }
        
        # --- version guard ------------------------------------------------
        license_version = data.get('license', {}).get('erp_version')
        logger.info(f"License ERP version: {license_version}")
        logger.info(f"Current ERP version: {erp_version}")
        
        if license_version != erp_version:
            msg = (
                f"Version Mismatch: License is for ERP version {license_version}, "
                f"but you are running version {erp_version}. "
                f"Please contact your vendor for a compatible license."
            )
            logger.error("[validate_with_generator] %s", msg)
            return {'success': False, 'message': msg}
        
        logger.info("✅ Validation successful - all checks passed")
        return data  # success path

    except requests.exceptions.Timeout:
        logger.error("❌ Generator API timeout")
        return {'success': False, 'message': 'Generator API timeout. Please try again.'}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Cannot connect to generator: {e}")
        return {'success': False, 'message': 'Cannot connect to license server. Please check if the generator is running.'}
    except Exception as exc:
        logger.exception("[validate_with_generator] Unexpected error")
        return {'success': False, 'message': f'Error: {str(exc)}'}



def confirm_with_generator(license_key, company_id, company_name,
                           company_gst):
    """
    Phase 3 – tell the generator that ERP has persisted the license.

    Errors are swallowed on purpose: by the time we reach Phase 3 the
    license is already saved locally, so a transient generator failure
    must not roll back a successful activation.
    """
    try:
        requests.post(
            f"{settings.LICENSE_GENERATOR_API_URL}/api/activate/",
            json={
                'license_key': license_key,
                'company_id': company_id,
                'company_name': company_name,
                'company_gst': company_gst,
                'erp_confirmed': True,
                'erp_version': ERP_VERSION,
            },
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
    except Exception:                                       # noqa: broad
        logger.warning(
            "[confirm_with_generator] Confirmation failed for key=%s (non-fatal)",
            license_key, exc_info=True,
        )


def is_stock_management_on_delivery(request=None, company=None):
    """
    Resolve the effective STOCK_MANAGEMENT_ON_DELIVERY setting for a company.

    Priority:
      1. If `company` provided and has `stock_management_on_delivery` field, use it.
      2. If `request` provided, try to resolve company by `request.company_id` or `request.company_code`.
      3. Fall back to global Django setting `STOCK_MANAGEMENT_ON_DELIVERY`.
    """
    from django.conf import settings
    try:
        if company is not None:
            return bool(getattr(company, 'stock_management_on_delivery', True))

        if request is not None:
            company_id = getattr(request, 'company_id', None)
            company_code = getattr(request, 'company_code', None)
            from company.models import Company
            if company_id:
                cmp = Company.objects.using('default').filter(pk=company_id).first()
                if cmp is not None:
                    return bool(getattr(cmp, 'stock_management_on_delivery', True))
            if company_code:
                cmp = Company.objects.using('default').filter(company_code=company_code).first()
                if cmp is not None:
                    return bool(getattr(cmp, 'stock_management_on_delivery', True))
    except Exception:
        logger.exception('Error resolving company stock management setting')

    return getattr(settings, 'STOCK_MANAGEMENT_ON_DELIVERY', True)


# ---------------------------------------------------------------------------
# Date parsing helper  (shared by Phase 2 logic)
# ---------------------------------------------------------------------------

def _parse_date(date_str):
    """
    Parse an ISO-8601 date string (with or without trailing Z) into a
    ``datetime.date``.  Returns None if the string is empty/unparseable.
    """
    if not date_str:
        return None

    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except (ValueError, AttributeError) as exc:
        logger.warning("[_parse_date] Could not parse '%s': %s", date_str, exc)
        return None


# ---------------------------------------------------------------------------
# Core activation orchestrator  (Phase 1 → 2 → 3)
# ---------------------------------------------------------------------------

def activate_license_for_company(company, license_key, request):
    """
    Full three-phase license activation.
    
    ✅ FIXED: Now properly handles database context by fetching company 
    instance from the correct database before creating LicenseKey
    
    Parameters
    ----------
    company      : Company model instance  (from any database)
    license_key  : str                     (already stripped)
    request      : HttpRequest             (used for IP and database context)

    Returns
    -------
    dict
        On success:
            {
                "success": True,
                "message": "License activated successfully!",
                "license": <LicenseKey instance>,
            }
        On failure:
            {"success": False, "message": <str>}
    """
    from company_settings.models import LicenseKey
    from company.models import Company
    
    logger.info(
        "[activate_license_for_company] Starting activation for company=%s (%s), key=%s",
        company.id, company.name, license_key,
    )
    
    # Determine which database to use
    # For registration: use the company's assigned database
    # For post-login: use the request's company_db
    company_db = getattr(request, 'company_db', None) or company.db_name
    
    if not company_db:
        logger.error("[activate_license_for_company] No database context available")
        return {
            'success': False,
            'message': 'Database context not available. Please try again.'
        }
    
    logger.info(f"[activate_license_for_company] Using database: {company_db}")
    
    # ------------------------------------------------------------------
    # Phase 1 – validate with generator (includes version check)
    # ------------------------------------------------------------------
    generator_response = validate_with_generator(
        license_key=license_key,
        company_id=company.id,
        company_name=company.name,
        company_gst=company.tax_id,
        erp_version=ERP_VERSION,
    )
    
    if not generator_response['success']:
        logger.error(
            "[activate_license_for_company] Phase 1 failed: %s",
            generator_response.get('message'),
        )
        return generator_response
    
    license_data = generator_response['license']
    logger.info(
        "[activate_license_for_company] Phase 1 passed. "
        "erp_version=%s, expiry=%s",
        license_data.get('erp_version'),
        license_data.get('expiry_date'),
    )
    
    # ------------------------------------------------------------------
    # Phase 2 – persist to ERP database
    # ------------------------------------------------------------------
    issue_date   = _parse_date(license_data.get('issue_date'))
    expiry_date  = _parse_date(license_data.get('expiry_date'))
    activation_ip = get_client_ip(request)
    
    try:
        # ✅ CRITICAL FIX: Fetch the company instance FROM the company database
        # This ensures the company object has the correct _state.db set
        company_in_db = Company.objects.using(company_db).get(id=company.id)
        logger.info(f"[activate_license_for_company] Fetched company from {company_db}: {company_in_db}")
        
        # ✅ FIX: Use explicit .using(company_db) for database routing
        # The router will now properly detect instance._state.db during foreign key assignment
        with transaction.atomic(using=company_db):
            license_obj, created = LicenseKey.objects.using(company_db).update_or_create(
                company=company_in_db,  # ✅ Use company instance with correct _state.db
                defaults={
                    'license_key':      license_data['license_key'],
                    'company_gst':      license_data.get('company_gst'),
                    'company_pan':      license_data.get('company_pan'),
                    'issue_date':       issue_date,
                    'expiry_date':      expiry_date,
                    'is_active':        True,
                    'is_license_expired': False,  #  CRITICAL FIX: Reset expired flag on activation!
                    'max_users':        license_data.get('max_users', 10),
                    'max_locations':    license_data.get('max_locations', 5),
                    'module_access':    license_data.get('module_access', {}),
                    'erp_version':      license_data.get('erp_version', ERP_VERSION),
                    'license_version':  license_data.get('license_version', 1),
                    'activated_at':     timezone.now(),
                    'activation_ip':    activation_ip,
                    'notes': (
                        f"Activated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                },
            )
        
        action = "created" if created else "updated"
        logger.info(
            "[activate_license_for_company] Phase 2 – license %s: %s (db: %s)",
            action, license_obj.license_key, company_db,
        )
        
        # 🔥 EXPLICIT FORCE-RESET: Ensure expired flag is definitely False
        # This is critical for renewals where the flag was previously True
        reset_result = LicenseKey.objects.using(company_db).filter(
            company_id=company.id
        ).update(is_license_expired=False)
        logger.info(
            "[activate_license_for_company] Force-reset is_license_expired=False: %d rows affected",
            reset_result,
        )
    
    except Exception as exc:
        logger.exception("[activate_license_for_company] Phase 2 DB error")
        return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    # ------------------------------------------------------------------
    # Phase 3 – confirm with generator  (fire-and-forget)
    # ------------------------------------------------------------------
    confirm_with_generator(
        license_key=license_key,
        company_id=company.id,
        company_name=company.name,
        company_gst=company.tax_id,
    )
    
    logger.info(
        "[activate_license_for_company] All three phases complete for company=%s (db=%s)",
        company.id, company_db,
    )
    
    return {
        'success': True,
        'message': 'License activated successfully!',
        'license': license_obj,
    }


# ---------------------------------------------------------------------------
# Response serialiser
# ---------------------------------------------------------------------------

def build_license_response(license_obj):
    """
    Turn a ``LicenseKey`` instance into the JSON-safe dict that the
    front-end expects.  Used by both registration and company-setup
    views so the payload shape never drifts apart.
    """
    days_remaining = 0
    if license_obj.expiry_date:
        days_remaining = (license_obj.expiry_date - timezone.now().date()).days

    is_expired = (
        license_obj.is_expired()
        if hasattr(license_obj, 'is_expired')
        else (days_remaining < 0)
    )

    return {
        'id':               license_obj.id,
        'license_key':      license_obj.license_key,
        'company_gst':      license_obj.company_gst,
        'company_pan':      license_obj.company_pan,
        'issue_date':       license_obj.issue_date.isoformat()  if license_obj.issue_date  else None,
        'expiry_date':      license_obj.expiry_date.isoformat() if license_obj.expiry_date else None,
        'is_active':        license_obj.is_active,
        'is_expired':       is_expired,
        'max_users':        license_obj.max_users,
        'max_locations':    license_obj.max_locations,
        'module_access':    license_obj.module_access,
        'erp_version':      license_obj.erp_version,
        'license_version':  license_obj.license_version,
        'days_remaining':   max(days_remaining, 0),
    }


# ---------------------------------------------------------------------------
# Key generation  (used during license *creation*, not activation)
# ---------------------------------------------------------------------------

def generate_license_key(company_id):
    """Generate a deterministic-looking license key from company_id + UUID."""
    raw = f"{company_id}-{uuid.uuid4()}"
    return hashlib.sha256(raw.encode()).hexdigest().upper()


# ---------------------------------------------------------------------------
# Default module-access map
# ---------------------------------------------------------------------------

def get_default_module_access():
    """Return {module_code: False} for every module in SYSTEM_MODULES."""
    return {module["code"]: False for module in SYSTEM_MODULES}


# ---------------------------------------------------------------------------
# license_required  view decorator
# ---------------------------------------------------------------------------

def license_required(module_code):
    """
    Decorator that gates a view behind:
        1. A valid company on the user
        2. An active, non-expired license
        3. module_access[module_code] == True
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            company = getattr(request.user, 'company', None)

            if not company:
                messages.error(request, "No license found for your company")
                return redirect_with_company("license_required")

            license_obj = company.license                  # OneToOne reverse

            if not license_obj.is_active or license_obj.is_expired():
                messages.error(request, "License expired or inactive")
                return redirect_with_company("license_expired")

            if not license_obj.has_module_access(module_code):
                messages.error(request, "Module not enabled in your license")
                return redirect_with_company("module_not_allowed")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator