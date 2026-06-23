"""
INTEGRATED COMPANY REGISTRATION – Multi-Tenant ERP

FIX: register_company_info now uses Company.objects.using('default').filter().update()
     instead of company.save(using='default') so the model's custom save() method
     never gets a chance to let the router override the target database.

FIX 2: register_fiscal_year now saves FY data to SESSION only (not DB) because
        the company DB migration hasn't run yet at Step 2. complete_registration()
        flushes the pending FY to the company DB after migration finishes.
"""

from django.shortcuts import render, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import logging
from django.db.models import Q

from company.models import Company
from bank.models import Bank
from company_settings.models import LocationType
from Lyraerp.utils.db_utils import register_database
from currencies.services import base_currency_code_from_country, ensure_base_currency_row
from chart_of_accounts.services import ensure_tax_accounts_for_type, sync_chart_of_accounts_from_company
from django.conf import settings
# from django_countries import countries
from cities_light.models import Country as WorldCountry
from cities_light.models import Region as WorldRegion
from cities_light.models import City as WorldCity
from location_utils import country_code_from_value, resolve_location_value, world_locations_ready

from company.utils import (
    activate_license_for_company,
    build_license_response,
)

logger = logging.getLogger(__name__)


def _world_locations_ready():
    return world_locations_ready()


def _world_country_choices():
    if not _world_locations_ready():
        return []

    return list(WorldCountry.objects.order_by("name").values_list("code2", "name"))


def _resolve_location_value(value, model):
    return resolve_location_value(value, model)


def _resolve_initial_location(company):
    country_code = ""
    state_id = ""
    city_id = ""

    try:
        country_code = (getattr(company.country, "code", "") or "").strip().upper()
    except Exception:
        country_code = str(getattr(company, "country", "") or "").strip().upper()

    if country_code and company.state:
        state = (
            WorldRegion.objects.filter(country__code2=country_code)
            .filter(Q(name__iexact=company.state) | Q(display_name__iexact=company.state))
            .first()
        )
        if state:
            state_id = state.id

    if country_code and company.city:
        city_qs = WorldCity.objects.filter(country__code2=country_code)
        if state_id:
            city_qs = city_qs.filter(region_id=state_id)
        city = city_qs.filter(Q(name__iexact=company.city) | Q(display_name__iexact=company.city)).first()
        if not city:
            city = WorldCity.objects.filter(
                country__code2=country_code
            ).filter(Q(name__iexact=company.city) | Q(display_name__iexact=company.city)).first()
        if city:
            city_id = city.id
            if not state_id and city.region_id:
                state_id = city.region_id

    return country_code, state_id, city_id



# =====================================================
# STEP 0: COMPANY REGISTRATION FORM  (GET)
# =====================================================

def company_registration(request, company_code=None):
    """
    Render the registration/setup page.
    """
    logger.info("[COMPANY REG] View accessed")
    logger.info("[COMPANY REG] Company code from URL: %s", company_code)
    logger.info("[COMPANY REG] Session keys: %s", list(request.session.keys()))

    if company_code:
        request.session['company_code'] = company_code
        request.session.modified = True
        logger.info("[COMPANY REG] Stored company code in session: %s", company_code)

    company_id = request.session.get('setup_company_id') or request.session.get('company_id')
    company_db = request.session.get('company_db', 'default')

    logger.info("[COMPANY REG] setup_company_id: %s", request.session.get('setup_company_id'))
    logger.info("[COMPANY REG] company_id: %s", request.session.get('company_id'))
    logger.info("[COMPANY REG] Using company_id: %s", company_id)

    if not company_id:
        logger.warning("[COMPANY REG] No company_id in session → signup")
        messages.error(request, "No company context found. Please signup or login again.")
        return redirect_with_company('signup')

    logger.info("[COMPANY REG] Company ID: %s, DB: %s", company_id, company_db)

    if company_db != 'default':
        try:
            register_database(company_db)
            logger.info("[COMPANY REG] Registered database: %s", company_db)
        except Exception as exc:
            logger.error("[COMPANY REG] Failed to register database: %s", exc)

    # country_code_value = ''
    # country_name = ''
    # initial_state = ''
    company = None
    setup_already_complete = False

    try:
        company = Company.objects.using('default').get(pk=company_id)
        logger.info("[COMPANY REG] Loaded company: %s", company.name)

        if company.setup_complete:
            logger.info("[COMPANY REG] Setup already complete - showing license activation form")
            setup_already_complete = True

        if company.country:
            # country_code_value = company.country.code
            # country_name = company.country.name
            # logger.info(f"[COMPANY REG] Country: {country_code_value} / {country_name}")
            logger.info(f"[COMPANY REG] Country: {company.country.code} / {company.country.name}")

        else:
            logger.warning("[COMPANY REG] No country set for company")

        # initial_state = company.state or ''

    except Company.DoesNotExist:
        logger.error("[COMPANY REG] Company not found: %s", company_id)
        messages.error(request, "Company not found")
        return redirect_with_company('signup')
    except Exception as exc:
        logger.error(f"[COMPANY REG] Error loading company: {exc}", exc_info=True)
        messages.error(request, "Error loading company information")
        return redirect_with_company('signup')

    has_license = False
    try:
        from company_settings.models import LicenseKey
        has_license = LicenseKey.objects.using(company_db).filter(
            company_id=company_id,
            is_active=True
        ).exists()
        logger.info(f"[COMPANY REG] Has license: {has_license}")
    except Exception as e:
        logger.warning(f"[COMPANY REG] Could not check license: {e}")

    initial_country_code, initial_state_id, initial_city_id = _resolve_initial_location(company)

    resolved_db_name = (
        (company.db_name or '').strip()
        or
        (company_db if company_db != 'default' else '')
    )
    logger.info("[COMPANY REG] Resolved company_db_name: '%s'", resolved_db_name)

    context = {
        'company':                  company,
        'banks':                    Bank.objects.using(company_db).all() if company_db != 'default' else [],
        'location_types':           LocationType.objects.using(company_db).filter(status=True) if company_db != 'default' else [],
        # 'countries':                countries,
        'countries':                _world_country_choices(),
        'world_locations_ready':    _world_locations_ready(),
        'is_registration':          True,
        'license_api_url':          settings.LICENSE_GENERATOR_API_URL,
        'initial_country_code':     initial_country_code,
        'initial_state_id':         initial_state_id,
        'initial_city_id':          initial_city_id,
        # 'initial_country_name':     country_name,
        # 'initial_state':            initial_state,
        'setup_already_complete':   setup_already_complete,
        'has_license':              has_license,
        'company_code':             company_code,
        'company_db_name':          resolved_db_name,
    }

    # Provide an inferred base currency for UI prefill (Zoho-like behaviour)
    try:
        from currencies.services import infer_currency_code_from_country
        inferred_code = infer_currency_code_from_country(company.country) if company and getattr(company, 'country', None) else ''
    except Exception:
        inferred_code = ''
    context['inferred_base_currency'] = inferred_code

    logger.info(
        "[COMPANY REG] Rendering: company_db_name='%s', setup_complete=%s, has_license=%s",
        resolved_db_name, setup_already_complete, has_license
    )

    return render(request, 'company/company_registration.html', context)


# =====================================================
# STEP 1: SAVE COMPANY INFORMATION  (POST)
# =====================================================

@require_http_methods(["POST"])
@ensure_csrf_cookie
def register_company_info(request, company_code=None):
    """
    Persist the organisation details entered on Step 1.

    FIX: Uses Company.objects.using('default').filter(pk=...).update(**fields)
    for the master DB write instead of company.save(using='default').
    """
    logger.info("=" * 80)
    logger.info("[REGISTER INFO] ========== VIEW CALLED ==========")

    try:
        company_id = request.session.get('setup_company_id') or request.session.get('company_id')
        company_db = request.session.get('company_db', 'default')

        logger.info("[REGISTER INFO] Company ID: %s | DB: %s", company_id, company_db)

        if not company_id:
            logger.error("[REGISTER INFO] No company context in session")
            return JsonResponse({
                'success': False,
                'message': 'No company context found. Please signup or login again.',
            }, status=400)

        name    = request.POST.get("name", "").strip()
        country = request.POST.get("country", "").strip()
        state   = request.POST.get("state", "").strip()
        city    = request.POST.get("city", "").strip()
        tax_type = (request.POST.get("tax_type") or "GST").strip()
        tax_id = request.POST.get("tax_id", "").strip()

        if country.isdigit():
            country_obj = WorldCountry.objects.filter(pk=int(country)).first()
            country = country_obj.code2 if country_obj else ""

        state = _resolve_location_value(state, WorldRegion)
        city = _resolve_location_value(city, WorldCity)

        if not tax_type:
            tax_type = "GST"

        logger.info(
            "[REGISTER INFO] name='%s' country='%s' state='%s' city='%s' tax_type='%s'",
            name, country, state, city, tax_type
        )
        
        if not name:
            return JsonResponse({'success': False, 'message': 'Organization name is required'}, status=400)
        if not country:
            return JsonResponse({'success': False, 'message': 'Country is required'}, status=400)
        if not state:
            return JsonResponse({'success': False, 'message': 'State is required'}, status=400)

        # Validate tax_type is one of the allowed choices
        valid_tax_types = ['GST', 'VAT', 'SALES', 'TURNOVER', 'NONE']
        if tax_type not in valid_tax_types:
            logger.warning("[REGISTER INFO] Invalid tax_type submitted: %s", tax_type)
            return JsonResponse({'success': False, 'message': 'Invalid Tax Type'}, status=400)

        if tax_type == 'NONE':
            tax_id = ''
        elif not tax_id:
            return JsonResponse({'success': False, 'message': 'Tax ID is required'}, status=400)

        logger.info("[REGISTER INFO] Required fields validated ✅")

        try:
            company = Company.objects.using('default').get(pk=company_id)
            logger.info(
                "[REGISTER INFO] Found company in master DB: %s (ID=%s), current tax_type=%s",
                company.name, company.id, company.tax_type
            )
        except Company.DoesNotExist:
            logger.error("[REGISTER INFO] Company %s not found in master DB", company_id)
            return JsonResponse({'success': False, 'message': 'Company not found'}, status=404)

        logo_field_value = None
        logo_file = request.FILES.get("logo")
        if logo_file:
            logger.info("[REGISTER INFO] Logo uploaded: %s", logo_file.name)
            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage
            logo_path = f"company/logos/{logo_file.name}"
            saved_path = default_storage.save(logo_path, ContentFile(logo_file.read()))
            logo_field_value = saved_path
            logger.info("[REGISTER INFO] Logo saved to: %s", saved_path)

        fiscal_year = request.POST.get("fiscal_year_start", "").strip()

        form_contact_person = request.POST.get("contact_person", "").strip()
        form_contact_email  = request.POST.get("contact_email", "").strip()
        form_contact_phone  = request.POST.get("contact_phone", "").strip()

        base_currency = base_currency_code_from_country(country)

        update_fields = dict(
            name                   = name,
            legal_name             = request.POST.get("legal_name", "").strip(),
            company_id             = request.POST.get("company_id", "").strip(),
            address_line1          = request.POST.get("address_line1", "").strip(),
            address_line2          = request.POST.get("address_line2", "").strip(),
            city                   = city,
            state                  = state,
            country                = country,
            postal_code            = request.POST.get("postal_code", "").strip(),
            email                  = request.POST.get("email", "").strip() or company.email,
            phone                  = request.POST.get("phone", "").strip() or company.phone,
            fax                    = request.POST.get("fax", "").strip(),
            website                = request.POST.get("website", "").strip(),
            contact_person         = form_contact_person or company.contact_person,
            contact_email          = form_contact_email or company.contact_email,
            contact_phone          = form_contact_phone or company.contact_phone,
            tax_type               = tax_type,
            tax_id                 = tax_id,
            fiscal_year_start      = fiscal_year if fiscal_year else None,
            report_basis           = request.POST.get("report_basis", "accrual"),
            facebook               = request.POST.get("facebook", "").strip(),
            instagram              = request.POST.get("instagram", "").strip(),
            linkedin               = request.POST.get("linkedin", "").strip(),
            additional_information = request.POST.get("additional_information", "").strip(),
            base_currency          = base_currency,
            show_logo_in_print_pdf = request.POST.get("show_logo_in_print_pdf") == "on"
        )
        logger.info("[REGISTER INFO] Final tax_type for update: '%s' (POST='%s', company.tax_type='%s')",
                    update_fields['tax_type'], request.POST.get("tax_type", "").strip(), company.tax_type)


        if logo_field_value:
            update_fields['logo'] = logo_field_value
        logger.info("[REGISTER INFO] About to update master DB with tax_type='%s'", update_fields['tax_type'])
        with transaction.atomic(using='default'):
            rows_updated = Company.objects.using('default').filter(pk=company_id).update(**update_fields)

            if rows_updated == 0:
                logger.error("[REGISTER INFO] update() affected 0 rows in master DB for pk=%s", company_id)
                return JsonResponse(
                    {'success': False, 'message': 'Company not found in master DB'},
                    status=404
                )

            logger.info(
                "[REGISTER INFO] Saved to MASTER DB via .update() ✅ "
                "(tax_type='%s', contact_person='%s'%s, contact_email='%s'%s)",
                update_fields['tax_type'],
                "(contact_person='%s'%s, contact_email='%s'%s)",
                update_fields['contact_person'],
                "" if form_contact_person else " [PRESERVED FROM SIGNUP]",
                update_fields['contact_email'],
                "" if form_contact_email else " [PRESERVED FROM SIGNUP]",
            )

        for field, value in update_fields.items():
            setattr(company, field, value)

        if company_db != 'default':
            logger.info("[REGISTER INFO] Syncing to company DB: %s", company_db)
            try:
                register_database(company_db)

                with transaction.atomic(using=company_db):
                    company_local, created = Company.objects.using(company_db).get_or_create(
                        id=company.id,
                        defaults={'name': company.name},
                    )
                    for field, value in update_fields.items():
                        setattr(company_local, field, value)
                    company_local.save(using=company_db)
                    ensure_base_currency_row(company_local, company_db, base_currency)
                    ensure_tax_accounts_for_type(tax_type, using=company_db)
                    sync_chart_of_accounts_from_company(company_local)
                    logger.info("[REGISTER INFO] Synced to company DB: %s ✅", company_db)

            except Exception as exc:
                logger.error("[REGISTER INFO] Sync to company DB failed: %s", exc, exc_info=True)

        request.session['registration_step'] = 1
        if 'company_id' not in request.session:
            request.session['company_id'] = company.id
        request.session.modified = True

        logger.info("[REGISTER INFO] ========== SUCCESS ==========")

        return JsonResponse({
            'success':      True,
            'message':      'Company information saved successfully!',
            'company_id':   company.id,
            'company_name': name,
        })

    except Exception as exc:
        logger.error("[REGISTER INFO] UNEXPECTED ERROR: %s", exc, exc_info=True)
        return JsonResponse({
            'success':    False,
            'message':    f'Server error: {str(exc)}',
            'error_type': type(exc).__name__,
        }, status=500)


@require_http_methods(["GET"])
def load_countries(request):
    if not _world_locations_ready():
        return JsonResponse({"countries": []})

    countries = WorldCountry.objects.order_by("name")
    return JsonResponse(
        {
            "countries": [
                {
                    "code": country.code2,
                    "name": country.name,
                    "dial_code": (country.phone or "").split(",", 1)[0].strip(),
                }
                for country in countries
            ]
        }
    )


@require_http_methods(["GET"])
def load_states(request):
    country_code = country_code_from_value(request.GET.get("country_code"))
    if not country_code or not _world_locations_ready():
        return JsonResponse({"states": []})

    states = WorldRegion.objects.filter(country__code2=country_code).order_by("name")
    return JsonResponse(
        {
            "states": [
                {"id": state.id, "name": state.display_name or state.name}
                for state in states
            ]
        }
    )


@require_http_methods(["GET"])
def load_cities(request):
    if not _world_locations_ready():
        return JsonResponse({"cities": []})

    state_id = (request.GET.get("state_id") or "").strip()
    country_code = country_code_from_value(request.GET.get("country_code"))

    if state_id and state_id.isdigit():
        cities = WorldCity.objects.filter(region_id=state_id)
    elif state_id and country_code:
        region = (
            WorldRegion.objects.filter(country__code2=country_code)
            .filter(Q(name__iexact=state_id) | Q(display_name__iexact=state_id))
            .first()
        )
        cities = WorldCity.objects.filter(region=region) if region else WorldCity.objects.none()
    elif country_code:
        cities = WorldCity.objects.filter(country__code2=country_code)
    else:
        return JsonResponse({"cities": []})

    cities = cities.order_by("name")
    return JsonResponse(
        {
            "cities": [
                {"id": city.id, "name": city.display_name or city.name}
                for city in cities
            ]
        }
    )


# =====================================================
# STEP 2: FISCAL YEAR  (POST)
# =====================================================

@require_http_methods(["POST"])
@ensure_csrf_cookie
def register_fiscal_year(request, company_code=None):
    """
    Step 2 of registration — stores fiscal year fields in the SESSION ONLY.

    WHY SESSION AND NOT DB:
        At this point in the setup wizard the company database migration
        hasn't finished yet, so system_settings_fiscalyear table doesn't
        exist yet.  Writing directly here causes:
            OperationalError: Table 'xxx.system_settings_fiscalyear' doesn't exist

        complete_registration() runs AFTER migration and calls
        _create_pending_fiscal_year() to flush the session data to the DB.
    """
    logger.info("=" * 80)
    logger.info("[REGISTER FY] ========== VIEW CALLED ==========")

    try:
        company_id = request.session.get('setup_company_id') or request.session.get('company_id')
        company_db = request.session.get('company_db', 'default')

        logger.info("[REGISTER FY] Company ID: %s | DB: %s", company_id, company_db)

        if not company_id:
            return JsonResponse({
                'success': False,
                'message': 'No company context found. Please complete Step 1 first.',
            }, status=400)

        # ── Parse & validate ──────────────────────────────────────────────────
        fy_name    = request.POST.get('fy_name', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date   = request.POST.get('end_date', '').strip()
        status     = request.POST.get('status', 'active').strip()

        logger.info("[REGISTER FY] name='%s' start='%s' end='%s' status='%s'",
                    fy_name, start_date, end_date, status)

        if not fy_name:
            return JsonResponse({'success': False, 'message': 'Fiscal Year name is required'}, status=400)
        if not start_date:
            return JsonResponse({'success': False, 'message': 'Start date is required'}, status=400)
        if not end_date:
            return JsonResponse({'success': False, 'message': 'End date is required'}, status=400)

        from datetime import datetime
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end   = datetime.strptime(end_date,   '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=400)

        if start >= end:
            return JsonResponse({
                'success': False,
                'message': 'Start date must be before end date.'
            }, status=400)

        # ── Save to SESSION — DB write happens in complete_registration() ─────
        request.session['pending_fiscal_year'] = {
            'fy_name':    fy_name,
            'start_date': start_date,
            'end_date':   end_date,
            'status':     status,
        }
        request.session['registration_step'] = 2
        request.session['fiscal_year_set']   = True
        request.session.modified = True

        logger.info("[REGISTER FY] FY data saved to session (will write to DB after migration) ✅")
        logger.info("[REGISTER FY] ========== SUCCESS ==========")

        return JsonResponse({
            'success':    True,
            'message':    f'Fiscal Year "{fy_name}" details saved!',
            'fy_name':    fy_name,
            'start_date': start_date,
            'end_date':   end_date,
        })

    except Exception as exc:
        logger.error("[REGISTER FY] UNEXPECTED ERROR: %s", exc, exc_info=True)
        return JsonResponse({
            'success':    False,
            'message':    f'Server error: {str(exc)}',
            'error_type': type(exc).__name__,
        }, status=500)


# =====================================================
# STEP 3: LICENSE ACTIVATION  (POST)
# =====================================================

@require_http_methods(["POST"])
def register_license_activation(request, company_code=None):
    """
    Activate a license key during first-time registration.
    License key is optional for free trial signups.
    """
    logger.info("[LICENSE ACTIVATION] ========== VIEW CALLED ==========")

    try:
        try:
            data = json.loads(request.body)
            logger.info("[LICENSE ACTIVATION] JSON parsed ✅")
        except json.JSONDecodeError as exc:
            logger.error("[LICENSE ACTIVATION] Invalid JSON: %s", exc)
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)

        company_id = request.session.get('setup_company_id') or request.session.get('company_id')
        logger.info("[LICENSE ACTIVATION] Company ID from session: %s", company_id)

        if not company_id:
            return JsonResponse({
                'success': False,
                'message': 'Please complete company information first',
            }, status=400)

        try:
            company = Company.objects.using('default').get(pk=company_id)
            logger.info("[LICENSE ACTIVATION] Found company: %s", company.name)
        except Company.DoesNotExist:
            logger.error("[LICENSE ACTIVATION] Company not found: %s", company_id)
            return JsonResponse({
                'success': False,
                'message': 'Company not found. Please complete company information first.',
            }, status=404)

        request.company_db = company.db_name or request.session.get('company_db', 'default')
        logger.info(f"[LICENSE ACTIVATION] request.company_db = {request.company_db}")

        is_trial = company.trial_active
        logger.info(f"[LICENSE ACTIVATION] is_trial: {is_trial}")

        license_key = data.get('license_key', '').strip()

        if not license_key:
            if not is_trial:
                return JsonResponse(
                    {'success': False, 'message': 'License key is required'},
                    status=400
                )

            logger.info("[LICENSE ACTIVATION] Trial company — skipping license activation")

            request.session['registration_step'] = 3
            request.session['license_activated'] = False
            request.session.modified = True

            logger.info("[LICENSE ACTIVATION] ========== SUCCESS (TRIAL, NO LICENSE) ==========")

            return JsonResponse({
                'success':  True,
                'message':  'Free trial setup complete!',
                'is_trial': True,
                'license':  None,
            })

        logger.info("[LICENSE ACTIVATION] Activating license: %s", license_key)

        result = activate_license_for_company(company, license_key, request)

        if not result['success']:
            return JsonResponse(result, status=400)

        license_obj = result['license']

        request.session['registration_step'] = 3
        request.session['license_activated']  = True
        request.session.modified              = True

        logger.info("[LICENSE ACTIVATION] ========== SUCCESS ==========")

        return JsonResponse({
            'success':  True,
            'message':  'License activated successfully!',
            'is_trial': is_trial,
            'license':  build_license_response(license_obj),
        })

    except Exception as exc:
        logger.error("[LICENSE ACTIVATION] Error: %s", exc, exc_info=True)
        return JsonResponse(
            {'success': False, 'message': f'Error: {str(exc)}'},
            status=500
        )


# =====================================================
# STEP 4: COMPLETE REGISTRATION  (GET)
# =====================================================

def complete_registration(request, company_code=None):
    """
    Mark setup_complete = True and first_login_completed = True in both
    databases and redirect to dashboard.

    CHANGE: Now calls _create_pending_fiscal_year() to flush the FY that
    was saved to the session in register_fiscal_year().  This runs AFTER
    migration so the system_settings_fiscalyear table is guaranteed to exist.
    """
    company_id = request.session.get('setup_company_id') or request.session.get('company_id')
    company_db = request.session.get('company_db', 'default')

    logger.info("[COMPLETE REG] Company ID: %s | DB: %s", company_id, company_db)

    if not company_id:
        logger.error("[COMPLETE REG] No company context")
        messages.error(request, "No company context found")
        return redirect_with_company('signup')

    try:
        company = Company.objects.using('default').get(pk=company_id)

        if company.setup_complete and company.first_login_completed:
            logger.info("[COMPLETE REG] Already complete — redirecting to dashboard")
            request.session.pop('setup_company_id', None)
            request.session.pop('setup_user_id', None)
            request.session.pop('registration_step', None)
            request.session.pop('pending_fiscal_year', None)
            request.session['registration_complete'] = True
            request.session.modified = True

            messages.success(request, f"Welcome to {company.name}!")
            company_code = company.company_code or request.session.get('company_code')
            if company_code:
                return redirect_with_company('index', company_code=company_code)
            return redirect_with_company('index')

        # ── Master DB ─────────────────────────────────────────────────────────
        base_currency = (getattr(company, "base_currency", None) or "").strip().upper()[:3]
        if not base_currency:
            base_currency = base_currency_code_from_country(company.country)
        Company.objects.using('default').filter(pk=company_id).update(
            setup_complete=True,
            first_login_completed=True,
            base_currency=base_currency,
        )
        company.base_currency = base_currency
        logger.info("[COMPLETE REG] Master DB updated ✅")

        # ── Company DB ────────────────────────────────────────────────────────
        if company_db != 'default':
            try:
                register_database(company_db)
                Company.objects.using(company_db).filter(pk=company_id).update(
                    setup_complete=True,
                    first_login_completed=True,
                    base_currency=base_currency,
                )
                company_local = Company.objects.using(company_db).filter(pk=company_id).first()
                if company_local:
                    ensure_base_currency_row(company_local, company_db, base_currency)
                logger.info("[COMPLETE REG] Company DB updated ✅")
            except Exception as exc:
                logger.error("[COMPLETE REG] Failed to update company DB: %s", exc, exc_info=True)

        # ── NEW: flush pending Fiscal Year now that migration has run ─────────
        _create_pending_fiscal_year(request, company_db)

        logger.info(
            "[COMPLETE REG] setup_complete=True, first_login_completed=True for pk=%s ✅",
            company_id
        )

        request.session.pop('setup_company_id', None)
        request.session.pop('setup_user_id', None)
        request.session.pop('registration_step', None)
        request.session.pop('pending_fiscal_year', None)
        request.session['registration_complete'] = True
        request.session.modified = True

        messages.success(request, f"🎉 {company.name} setup complete!")

        company_code = company.company_code or request.session.get('company_code')
        if company_code:
            return redirect_with_company('index', company_code=company_code)
        return redirect_with_company('index')

    except Company.DoesNotExist:
        logger.error("[COMPLETE REG] Company not found: %s", company_id)
        messages.error(request, "Company not found")
        return redirect_with_company('signup')


# =====================================================
# PRIVATE HELPER: flush pending FY from session → DB
# =====================================================

def _create_pending_fiscal_year(request, company_db):
    """
    Reads 'pending_fiscal_year' from the session and writes it to the
    company database.  Called from complete_registration() only, after
    the database migration has finished and the FY table exists.

    Safe to call multiple times — uses get_or_create internally.
    """
    fy_data = request.session.get('pending_fiscal_year')

    if not fy_data:
        logger.info("[FY FLUSH] No pending fiscal year in session — skipping")
        return

    if company_db == 'default':
        logger.warning("[FY FLUSH] company_db is 'default' — skipping fiscal year creation")
        return

    fy_name    = fy_data.get('fy_name', '').strip()
    start_date = fy_data.get('start_date', '').strip()
    end_date   = fy_data.get('end_date', '').strip()
    status     = fy_data.get('status', 'active').strip()

    if not (fy_name and start_date and end_date):
        logger.warning("[FY FLUSH] Incomplete FY data in session: %s", fy_data)
        return

    from datetime import datetime
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end   = datetime.strptime(end_date,   '%Y-%m-%d').date()
    except ValueError:
        logger.error("[FY FLUSH] Invalid date values in session: %s", fy_data)
        return

    try:
        from system_settings.models import FiscalYear

        with transaction.atomic(using=company_db):
            fy, created = FiscalYear.objects.using(company_db).get_or_create(
                name=fy_name,
                defaults={
                    'start_date': start,
                    'end_date':   end,
                    'status':     status,
                    'created_by': request.user if request.user.is_authenticated else None,
                }
            )

            if not created:
                fy.start_date = start
                fy.end_date   = end
                fy.status     = status
                fy.save(using=company_db, update_fields=['start_date', 'end_date', 'status'])

            # Update Company's fiscal_year_start field
            company_id = request.session.get('setup_company_id') or request.session.get('company_id')
            if company_id:
                Company.objects.using('default').filter(pk=company_id).update(
                    fiscal_year_start=start
                )
                if company_db != 'default':
                    Company.objects.using(company_db).filter(pk=company_id).update(
                        fiscal_year_start=start
                    )
                logger.info(
                    "[FY FLUSH] Updated Company fiscal_year_start to '%s' ✅", start
                )    

        logger.info(
            "[FY FLUSH] FiscalYear '%s' %s in company DB '%s' ✅",
            fy_name, 'created' if created else 'updated', company_db
        )

    except Exception as exc:
        # Non-fatal: log and move on. User can add FY manually from Period Management.
        logger.error("[FY FLUSH] Failed to create FiscalYear: %s", exc, exc_info=True)


# =====================================================
# UTILITY: registration-status check  (GET)
# =====================================================

def check_registration_status(request, company_code=None):
    """Simple API endpoint — does a company exist and does it have a license?"""
    company_exists = Company.objects.exists()

    if company_exists:
        company     = Company.objects.first()
        has_license = hasattr(company, 'license') and company.license is not None
        return JsonResponse({
            'registration_complete': True,
            'company_exists':        True,
            'has_license':           has_license,
            'company_name':          company.name,
            'company_id':            company.id,
        })

    return JsonResponse({
        'registration_complete': False,
        'company_exists':        False,
        'has_license':           False,
    })
