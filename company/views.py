from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
import logging
from .models import Company
from company_settings.models import CompanyBankAccount, LocationType, Location
from bank.models import Bank
from django.core.files.base import ContentFile 
import requests 
from django.conf import settings 
from django_countries import countries
from Lyraerp.utils.db_utils import register_database
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from currencies.models import Currency
from currencies.services import base_currency_code_from_country, ensure_base_currency_row
from chart_of_accounts.services import ensure_tax_accounts_for_type, sync_chart_of_accounts_from_company
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def _redirect_to_settings_details_tab(request):
    settings_url = get_company_redirect_url(request, 'settings_page')
    return redirect(f"{settings_url}?tab=details")


# ---------------- LIST ----------------
@login_required
def company_list(request):
    companies = Company.objects.all().order_by("-id")
    return render(request, "company/list.html", {"companies": companies})

# ---------------- CREATE ----------------
@login_required
def company_create(request):
    banks = Bank.objects.all()
    location_types = LocationType.objects.filter(status=True)

    # ---- BLOCK MULTIPLE COMPANIES ----
    if Company.objects.exists():
        # AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Only one company is allowed. A company already exists.'
            }, status=400)

        # Normal request
        messages.warning(request, "Only one company is allowed. A company already exists.")
        return _redirect_to_settings_details_tab(request)

    if request.method == "POST":
        try:
            # Step 1: Read logo file
            logo_file = request.FILES.get("logo")
            logo_content = None
            logo_name = None

            if logo_file:
                logo_content = logo_file.read()
                logo_name = logo_file.name

            # Step 2: Create company
            company = Company()
            company.name = request.POST.get("name")
            company.legal_name = request.POST.get("legal_name")
            company.company_id = request.POST.get("company_id")
            company.address_line1 = request.POST.get("address_line1")
            company.address_line2 = request.POST.get("address_line2")
            company.city = request.POST.get("city")
            company.state = request.POST.get("state")
            company.country = request.POST.get("country") or "IN"
            company.postal_code = request.POST.get("postal_code")
            company.email = request.POST.get("email")
            company.phone = request.POST.get("phone")
            company.fax = request.POST.get("fax")
            company.website = request.POST.get("website")
            company.contact_person = request.POST.get("contact_person")
            company.contact_email = request.POST.get("contact_email")
            company.contact_phone = request.POST.get("contact_phone")
            company.tax_id = request.POST.get("tax_id")
            posted_base_currency = (request.POST.get("base_currency") or "").strip().upper()[:10]
            company.base_currency = posted_base_currency or base_currency_code_from_country(company.country)
            # Company-level credit limit (renamed from global_credit_limit)
            company.credit_limit = request.POST.get("credit_limit") or None

            fiscal_year = request.POST.get("fiscal_year_start")
            company.fiscal_year_start = fiscal_year if fiscal_year else None

            company.report_basis = request.POST.get("report_basis")
            company.facebook = request.POST.get("facebook")
            company.instagram = request.POST.get("instagram")
            company.linkedin = request.POST.get("linkedin")
            company.additional_information = request.POST.get("additional_information")
            company.terms_and_conditions = request.POST.get("terms_and_conditions")
            company.show_logo_in_print_pdf = request.POST.get("show_logo_in_print_pdf") == "on"
            company.status = True if request.POST.get("status") == "on" else False

            company.created_by = request.user
            company.updated_by = request.user

            # Step 3: Save logo if present
            if logo_content and logo_name:
                company.logo.save(logo_name, ContentFile(logo_content), save=False)

            # Step 4: Save company
            company.save()

            # ======================== DUAL-DB SYNC ========================
            # Sync to company-specific database if it exists
            if company.db_name and company.db_created:
                try:
                    logger.info("[COMPANY CREATE] Syncing to company DB: %s", company.db_name)
                    register_database(company.db_name)
                    
                    with transaction.atomic(using=company.db_name):
                        # Get or create company record in company DB
                        company_local, created = Company.objects.using(company.db_name).get_or_create(
                            id=company.id,
                            defaults={'name': company.name},
                        )
                        
                        # Update all fields in company DB
                        for field in [
                            'legal_name', 'company_id', 'address_line1', 'address_line2',
                            'city', 'state', 'country', 'postal_code', 'email', 'phone',
                            'fax', 'website', 'contact_person', 'contact_email', 'contact_phone',
                            'tax_id', 'base_currency', 'credit_limit', 'fiscal_year_start', 'report_basis',
                            'facebook', 'instagram', 'linkedin', 'additional_information',
                            'terms_and_conditions','show_logo_in_print_pdf', 'status', 'logo'
                        ]:
                            setattr(company_local, field, getattr(company, field))
                        
                        company_local.save(using=company.db_name)
                        ensure_base_currency_row(company_local, company.db_name, company.base_currency)
                        logger.info(
                            "[COMPANY CREATE] Synced to company DB: %s ✅ (tax_id='%s')",
                            company.db_name,
                            company.tax_id or 'N/A'
                        )
                        
                except Exception as sync_exc:
                    logger.error(
                        "[COMPANY CREATE] Failed to sync to company DB: %s", 
                        sync_exc, 
                        exc_info=True
                    )
                    # Non-fatal — master DB is the source of truth
            # ================================================================

            # AJAX success
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Company created successfully!',
                    'company_id': company.id
                })

            messages.success(request, "Company created successfully!")
            return _redirect_to_settings_details_tab(request)

        except Exception as e:
            import traceback
            print("Error creating company:")
            print(traceback.format_exc())

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error: {str(e)}'
                }, status=400)

            messages.error(request, f"Error creating company: {str(e)}")

    # Build base currency choices for create form.
    # Show a full ISO currency list (pycountry if available), but preselect an inferred code when possible.
    base_choices = []
    selected_base = None
    try:
        from currencies.utils import all_currency_choices
        base_choices = all_currency_choices()
    except Exception:
        base_choices = []

    country_val = (request.POST.get('country') if request.method == 'POST' else request.GET.get('country')) or None
    if country_val and base_choices:
        try:
            from currencies.services import infer_currency_code_from_country
            inferred = infer_currency_code_from_country(country_val) or ''
            inferred = (inferred or '').strip().upper()[:3]
            if inferred and inferred not in [c for c, _ in base_choices]:
                # Add inferred option at top if missing
                base_choices.insert(0, (inferred, inferred))
            if inferred:
                selected_base = inferred
        except Exception:
            pass

    if not selected_base:
        try:
            inferred_default = base_currency_code_from_country('IN') or ''
            inferred_default = inferred_default.strip().upper()[:3]
            if inferred_default:
                selected_base = inferred_default
                if selected_base not in [c for c, _ in base_choices]:
                    base_choices.insert(0, (selected_base, selected_base))
        except Exception:
            pass

    return render(request, "company/create.html", {
        "banks": banks,
        "location_types": location_types,
        'countries': countries,
        "license_api_url": settings.LICENSE_GENERATOR_API_URL,
        # For the base-currency select on the form (create)
        "base_currency_choices": base_choices,
        "selected_base_currency": selected_base,
    })

# ---------------- UPDATE ----------------
@login_required
def company_update(request, pk):
    # Always edit the master Company record in the default DB.
    # Tenant routing may point Company reads/writes to a company DB; that would
    # make tax_type updates appear to "not change" in default.
    company = get_object_or_404(Company.objects.using('default'), pk=pk)
    banks = Bank.objects.all()
    location_types = LocationType.objects.filter(status=True)

    if request.method == "POST":
        try:
            company.name = request.POST.get("name")
            company.legal_name = request.POST.get("legal_name")
            company.company_id = request.POST.get("company_id")
            company.address_line1 = request.POST.get("address_line1")
            company.address_line2 = request.POST.get("address_line2")
            company.city = request.POST.get("city")
            company.state = request.POST.get("state")
            company.country = request.POST.get("country")
            company.postal_code = request.POST.get("postal_code")
            company.email = request.POST.get("email")
            company.phone = request.POST.get("phone")
            company.fax = request.POST.get("fax")
            company.website = request.POST.get("website")
            company.contact_person = request.POST.get("contact_person")
            company.contact_email = request.POST.get("contact_email")
            company.contact_phone = request.POST.get("contact_phone")
            # tax_type is always GST - never allow changes
            company.tax_id = request.POST.get("tax_id")
            posted_base_currency = (request.POST.get("base_currency") or "").strip().upper()[:10]
            company.base_currency = posted_base_currency or base_currency_code_from_country(company.country)
            # Company-level credit limit (renamed from global_credit_limit)
            company.credit_limit = request.POST.get("credit_limit") or None

            # Handle empty date field
            fiscal_year = request.POST.get("fiscal_year_start")
            company.fiscal_year_start = fiscal_year if fiscal_year else None

            company.report_basis = request.POST.get("report_basis")
            company.facebook = request.POST.get("facebook")
            company.instagram = request.POST.get("instagram")
            company.linkedin = request.POST.get("linkedin")
            company.additional_information = request.POST.get("additional_information")
            company.terms_and_conditions = request.POST.get("terms_and_conditions")
            company.show_logo_in_print_pdf = request.POST.get("show_logo_in_print_pdf") == "on"
            company.status = True if request.POST.get("status") == "on" else False

            # Handle logo upload
            logo_file = request.FILES.get("logo")
            if logo_file:
                logo_content = logo_file.read()
                logo_name = logo_file.name
                company.logo.save(logo_name, ContentFile(logo_content), save=False)

            company.updated_by = request.user
            company.save(using='default')

            # ======================== DUAL-DB SYNC ========================
            # Sync updated fields to company-specific database if it exists
            sync_db_name = getattr(request, 'company_db', None) or getattr(company, 'db_name', None)
            if sync_db_name and sync_db_name != 'default':
                try:
                    logger.info("[COMPANY UPDATE] Syncing to company DB: %s", sync_db_name)
                    register_database(sync_db_name)
                    
                    with transaction.atomic(using=sync_db_name):
                        # Get or create company record in company DB
                        company_local, created = Company.objects.using(sync_db_name).get_or_create(
                            id=company.id,
                            defaults={'name': company.name},
                        )
                        
                        # Update all company info fields in company DB
                        for field in [
                            'legal_name', 'company_id', 'address_line1', 'address_line2',
                            'city', 'state', 'country', 'postal_code', 'email', 'phone',
                            'fax', 'website', 'contact_person', 'contact_email', 'contact_phone',
                            'tax_type','tax_id', 'base_currency', 'credit_limit', 'fiscal_year_start', 'report_basis',
                            'facebook', 'instagram', 'linkedin', 'additional_information',
                            'terms_and_conditions','show_logo_in_print_pdf', 'status', 'logo'
                        ]:
                            setattr(company_local, field, getattr(company, field))
                        
                        company_local.save(using=sync_db_name)
                        ensure_base_currency_row(company_local, sync_db_name, company.base_currency)
                        ensure_tax_accounts_for_type(company.tax_type, using=sync_db_name)
                        sync_chart_of_accounts_from_company(company_local)
                    logger.info(
                            "[COMPANY UPDATE] Synced to company DB: %s ✅ (tax_id='%s')",
                            sync_db_name,
                            company.tax_id or 'N/A'
                        )
                        
                except Exception as sync_exc:
                    logger.error(
                        "[COMPANY UPDATE] Failed to sync to company DB: %s", 
                        sync_exc, 
                        exc_info=True
                    )
                    # Non-fatal — master DB is the source of truth
            # ================================================================

            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Company updated successfully!',
                    'company_id': company.id
                })
            else:
                messages.success(request, "Company updated successfully!")
                return _redirect_to_settings_details_tab(request)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("Error updating company:")
            print(error_details)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error: {str(e)}'
                }, status=400)
            else:
                messages.error(request, f"Error updating company: {str(e)}")

    
    # Build base currency choices for update form. Prefer full ISO list but keep company's selection.
    try:
        from currencies.utils import all_currency_choices
        choices = all_currency_choices()
    except Exception:
        choices = [(c.code, c.code) for c in Currency.objects.filter(company=company).order_by('code')]
    selected = company.base_currency
    if not selected:
        try:
            from currencies.services import infer_currency_code_from_country
            inferred = infer_currency_code_from_country(getattr(company, 'country', None)) or ''
            inferred = (inferred or '').strip().upper()[:3]
            if inferred and inferred not in [c for c, _ in choices]:
                choices.insert(0, (inferred, inferred))
                selected = inferred
        except Exception:
            pass

    return render(request, "company/create.html", {
        "company": company,
        "banks": banks,
        "countries": countries,
        "location_types": location_types,
        "license_api_url": settings.LICENSE_GENERATOR_API_URL,
        "base_currency_choices": choices,
        "selected_base_currency": selected,
    })

# ---------------- DELETE ----------------
@login_required
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.delete()
    messages.success(request, "Company deleted successfully!")
    return _redirect_to_settings_details_tab(request)

# -----------------------------BANK------------------------------------------
@login_required
def company_bank_list(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    accounts = CompanyBankAccount.objects.filter(company=company)
    return render(request, "company/bank/list.html", {"company": company, "accounts": accounts})

# Fallback when no company exists yet
@login_required
def company_bank_list_no_company(request):
    accounts = []
    return render(request, "company/bank/list.html", {"company": None, "accounts": accounts})

@login_required
def company_bank_create(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    banks = Bank.objects.all()

    if request.method == "POST":
        account = CompanyBankAccount()
        account.company = company
        account.bank_id = request.POST.get("bank_id")
        account.account_name = request.POST.get("account_name")
        account.account_number = request.POST.get("account_number")
        account.ifsc_swift_code = request.POST.get("ifsc_swift_code")
        account.branch_name = request.POST.get("branch_name")
        account.is_default = True if request.POST.get("is_default") == "on" else False
        account.status = True if request.POST.get("status") == "on" else False

        account.created_by = request.user
        account.updated_by = request.user
        account.save()

        if account.is_default:
            CompanyBankAccount.objects.filter(company=company).exclude(id=account.id).update(is_default=False)

        messages.success(request, "Bank account added successfully!")
        return redirect_with_company("company_bank_list", company_id=company.id)

    return render(request, "company/bank/create.html", {"company": company, "banks": banks})

@login_required
def company_bank_update(request, pk):
    account = get_object_or_404(CompanyBankAccount, pk=pk)
    banks = Bank.objects.all()

    if request.method == "POST":
        account.bank_id = request.POST.get("bank_id")
        account.account_name = request.POST.get("account_name")
        account.account_number = request.POST.get("account_number")
        account.ifsc_swift_code = request.POST.get("ifsc_swift_code")
        account.branch_name = request.POST.get("branch_name")
        account.is_default = True if request.POST.get("is_default") == "on" else False
        account.status = True if request.POST.get("status") == "on" else False
        account.updated_by = request.user
        account.save()

        if account.is_default:
            CompanyBankAccount.objects.filter(company=account.company).exclude(id=account.id).update(is_default=False)

        messages.success(request, "Bank account updated successfully!")
        return redirect_with_company("company_bank_list", company_id=account.company.id)

    return render(
        request,
        "company/bank/create.html",
        {"account": account, "banks": banks, "company": account.company}
    )


@login_required
@require_GET
def infer_currency_for_country(request):
    country = request.GET.get('country') or request.GET.get('q') or None
    try:
        from currencies.services import infer_currency_code_from_country
        code = infer_currency_code_from_country(country) or ''
        code = (code or '').strip().upper()[:3]
        return JsonResponse({"success": True, "currency": code})
    except Exception:
        return JsonResponse({"success": False, "currency": ''})

@login_required
def company_bank_delete(request, pk):
    account = get_object_or_404(CompanyBankAccount, pk=pk)
    company_id = account.company.id
    account.delete()
    messages.success(request, "Bank account deleted successfully!")
    return redirect_with_company("company_bank_list", company_id=company_id)


@login_required
def bank_accounts_ajax_list(request):
    company_id = request.GET.get('company_id')
    if company_id:
        company = get_object_or_404(Company, pk=company_id)
        accounts = CompanyBankAccount.objects.filter(company=company).select_related('bank')
    else:
        accounts = []
    
    data = []
    for account in accounts:
        data.append({
            'id': account.id,
            'account_name': account.account_name,
            'bank_name': account.bank.bank_name if account.bank else '',
            'bank_id': account.bank.id if account.bank else None,  # ADD THIS LINE
            'account_number': account.account_number,
            'ifsc_swift_code': account.ifsc_swift_code,
            'branch_name': account.branch_name,
            'is_default': account.is_default,
        })
    return JsonResponse({'accounts': data})

@login_required
def bank_account_ajax_create(request):
    if request.method == "POST":
        try:
            company_id = request.POST.get('company_id')
            company = get_object_or_404(Company, pk=company_id)
            
            account = CompanyBankAccount()
            account.company = company
            account.bank_id = request.POST.get("bank")
            account.account_name = request.POST.get("account_name")
            account.account_number = request.POST.get("account_number")
            account.ifsc_swift_code = request.POST.get("ifsc_swift_code")
            account.branch_name = request.POST.get("branch_name")
            account.is_default = request.POST.get("is_default") == "on"
            account.status = True
            account.created_by = request.user
            account.updated_by = request.user
            account.save()

            if account.is_default:
                CompanyBankAccount.objects.filter(company=company).exclude(id=account.id).update(is_default=False)

            return JsonResponse({'success': True, 'message': 'Bank account added successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

@login_required
def bank_account_ajax_delete(request, pk):
    if request.method == "POST":
        try:
            account = get_object_or_404(CompanyBankAccount, pk=pk)
            account.delete()
            return JsonResponse({'success': True, 'message': 'Bank account deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)





@login_required
def bank_account_ajax_get(request, pk):
    """Get single bank account details for editing"""
    try:
        account = get_object_or_404(CompanyBankAccount, pk=pk)
        data = {
            'id': account.id,
            'bank_id': account.bank.id if account.bank else None,
            'account_name': account.account_name,
            'account_number': account.account_number,
            'ifsc_swift_code': account.ifsc_swift_code or '',
            'branch_name': account.branch_name or '',
            'is_default': account.is_default,
        }
        return JsonResponse({'success': True, 'account': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def bank_account_ajax_update(request, pk):
    """Update bank account"""
    if request.method == "POST":
        try:
            account = get_object_or_404(CompanyBankAccount, pk=pk)
            company_id = request.POST.get('company_id')
            company = get_object_or_404(Company, pk=company_id)
            
            account.bank_id = request.POST.get("bank")
            account.account_name = request.POST.get("account_name")
            account.account_number = request.POST.get("account_number")
            account.ifsc_swift_code = request.POST.get("ifsc_swift_code")
            account.branch_name = request.POST.get("branch_name")
            account.is_default = request.POST.get("is_default") == "on"
            account.updated_by = request.user
            account.save()

            # If this is set as default, unset others
            if account.is_default:
                CompanyBankAccount.objects.filter(company=company).exclude(id=account.id).update(is_default=False)

            return JsonResponse({'success': True, 'message': 'Bank account updated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

# ======================= ADD BANK =======================
def add_bank(request):
    """Add a new bank"""
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check authentication
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated request to add_bank")
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    try:
        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in add_bank: {str(e)}, body: {request.body[:200]}")
            return JsonResponse({'success': False, 'message': 'Invalid JSON request'}, status=400)
        
        bank_name = data.get('bank_name', '').strip()
        
        if not bank_name:
            return JsonResponse({'success': False, 'message': 'Bank name is required'}, status=400)
        
        logger.info(f"[ADD_BANK] Processing bank: {bank_name}, Company DB: {getattr(request, 'company_db', 'default')}")
        
        # Check if bank already exists
        existing_bank = Bank.objects.filter(bank_name__iexact=bank_name).first()
        if existing_bank:
            logger.info(f"[ADD_BANK] Bank already exists: {bank_name} (ID: {existing_bank.id})")
            return JsonResponse({
                'success': True, 
                'bank_id': existing_bank.id,
                'message': 'Bank already exists'
            })
        
        # Create new bank
        bank = Bank.objects.create(
            bank_name=bank_name,
            created_by=request.user,
            updated_by=request.user,
            status=True
        )
        
        logger.info(f"[ADD_BANK] Bank created successfully: {bank_name} (ID: {bank.id}) by user {request.user}")
        
        return JsonResponse({
            'success': True,
            'bank_id': bank.id,
            'message': 'Bank added successfully'
        })
        
    except Exception as e:
        logger.exception(f"[ADD_BANK] Error creating bank: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error: {str(e)[:100]}'}, status=400)

# ========================================================

# -----------------------------LOCATION TYPE--------------------------------
@login_required
def location_type_list(request):
    types = LocationType.objects.filter(status=True).order_by("-id")
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        data = [{'id': t.id, 'name': t.name} for t in types]
        return JsonResponse({'types': data})
    
    # Otherwise return template
    return render(request, "location/list.html", {"types": types})

@login_required
def location_type_create(request):
    if request.method == "POST":
        try:
            location_type = LocationType()
            location_type.name = request.POST.get("name")
            location_type.description = request.POST.get("description")
            location_type.status = True if request.POST.get("status") == "on" else False
            location_type.save()

            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Location Type created successfully!',
                    'id': location_type.id,
                    'name': location_type.name
                })
            else:
                messages.success(request, "Location Type created successfully!")
                return redirect_with_company(request, "location_type_list")
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
            else:
                messages.error(request, f"Error: {str(e)}")
                return render(request, "location/create.html")

    return render(request, "location/create.html")

@login_required
def location_type_update(request, pk):
    item = get_object_or_404(LocationType, pk=pk)

    if request.method == "POST":
        item.name = request.POST.get("name")
        item.description = request.POST.get("description")
        item.status = True if request.POST.get("status") == "on" else False
        item.save()

        messages.success(request, "Location Type updated successfully!")
        return redirect_with_company(request, "location_type_list")

    return render(request, "location/create.html", {"item": item})

@login_required
def location_type_delete(request, pk):
    item = get_object_or_404(LocationType, pk=pk)
    item.delete()
    messages.success(request, "Location Type deleted successfully!")
    return redirect_with_company(request, "location_type_list")

# ------------------------- LOCATION----------------------------------------
@login_required
def location_list(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    locations = Location.objects.filter(company=company).order_by("-id")

    return render(request, "location/list.html", {
        "company": company,
        "locations": locations
    })

# Fallback when no company is created yet
@login_required
def location_list_no_company(request):
    locations = []
    return render(request, "location/list.html", {
        "company": None,
        "locations": locations
    })

@login_required
def location_create(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    location_types = LocationType.objects.filter(status=True)

    if request.method == "POST":
        location = Location()
        location.company = company
        location.location_type_id = request.POST.get("location_type_id")
        location.name = request.POST.get("name")
        location.code = request.POST.get("code")

        location.display_capacity = request.POST.get("display_capacity")
        location.storage_capacity = request.POST.get("storage_capacity")
        location.gps_location = request.POST.get("gps_location")
        location.certification_number = request.POST.get("certification_number")
        location.service_capabilities = request.POST.get("service_capabilities")

        location.manager_name = request.POST.get("manager_name")
        location.manager_phone = request.POST.get("manager_phone")
        location.manager_email = request.POST.get("manager_email")

        location.address_line1 = request.POST.get("address_line1")
        location.address_line2 = request.POST.get("address_line2")
        location.city = request.POST.get("city")
        location.state = request.POST.get("state")
        location.country = request.POST.get("country")
        location.postal_code = request.POST.get("postal_code")

        location.phone = request.POST.get("phone")
        location.working_hours = request.POST.get("working_hours")

        location.status = True if request.POST.get("status") == "on" else False

        location.created_by = request.user
        location.updated_by = request.user
        location.save()

        messages.success(request, "Location created successfully!")
        return redirect_with_company("location_list", company_id=company.id)

    return render(request, "location/create.html", {
        "company": company,
        "countries": countries,
        "location_types": location_types
    })

@login_required
def location_update(request, pk):
    location = get_object_or_404(Location, pk=pk)
    location_types = LocationType.objects.filter(status=True)

    if request.method == "POST":
        location.location_type_id = request.POST.get("location_type_id")
        location.name = request.POST.get("name")
        location.code = request.POST.get("code")

        location.display_capacity = request.POST.get("display_capacity")
        location.storage_capacity = request.POST.get("storage_capacity")
        location.gps_location = request.POST.get("gps_location")
        location.certification_number = request.POST.get("certification_number")
        location.service_capabilities = request.POST.get("service_capabilities")

        location.manager_name = request.POST.get("manager_name")
        location.manager_phone = request.POST.get("manager_phone")
        location.manager_email = request.POST.get("manager_email")

        location.address_line1 = request.POST.get("address_line1")
        location.address_line2 = request.POST.get("address_line2")
        location.city = request.POST.get("city")
        location.state = request.POST.get("state")
        location.country = request.POST.get("country")
        location.postal_code = request.POST.get("postal_code")

        location.phone = request.POST.get("phone")
        location.working_hours = request.POST.get("working_hours")

        location.status = True if request.POST.get("status") == "on" else False

        location.updated_by = request.user
        location.save()

        messages.success(request, "Location updated successfully!")
        return redirect_with_company("location_list", company_id=location.company.id)

    return render(request, "location/create.html", {
        "location": location,
        "location_types": location_types,
        "countries": countries,
        "company": location.company
    })

@login_required
def location_delete(request, pk):
    location = get_object_or_404(Location, pk=pk)
    company_id = location.company.id
    location.delete()

    messages.success(request, "Location deleted successfully!")
    return redirect_with_company("location_list", company_id=company_id)

# AJAX endpoint for locations

@login_required
def locations_ajax_list(request):
    company_id = request.GET.get('company_id')
    if company_id:
        company = get_object_or_404(Company, pk=company_id)
        locations = Location.objects.filter(company=company).select_related('location_type')
    else:
        locations = []
    
    data = []
    for location in locations:
        data.append({
            'id': location.id,
            'name': location.name,
            'location_type': location.location_type.name if location.location_type else '',
            'location_type_id': location.location_type.id if location.location_type else None,
            'city': location.city,
            'state': location.state,
        })
    return JsonResponse({'locations': data})

@login_required
def location_ajax_create(request):
    if request.method == "POST":
        try:
            company_id = request.POST.get('company_id')
            company = get_object_or_404(Company, pk=company_id)
            
            location = Location()
            location.company = company
            location.location_type_id = request.POST.get("location_type")
            location.name = request.POST.get("name")
            location.code = request.POST.get("code")
            location.manager_name = request.POST.get("manager_name")
            location.manager_email = request.POST.get("manager_email")
            location.manager_phone = request.POST.get("manager_phone")
            location.address_line1 = request.POST.get("address_line1")
            location.address_line2 = request.POST.get("address_line2")
            location.city = request.POST.get("city")
            location.state = request.POST.get("state")
            location.country = request.POST.get("country")
            location.postal_code = request.POST.get("postal_code")
            location.phone = request.POST.get("phone")
            location.working_hours = request.POST.get("working_hours")
            location.status = True
            location.created_by = request.user
            location.updated_by = request.user
            location.save()

            return JsonResponse({'success': True, 'message': 'Location created successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

@login_required
def location_ajax_delete(request, pk):
    if request.method == "POST":
        try:
            location = get_object_or_404(Location, pk=pk)
            location.delete()
            return JsonResponse({'success': True, 'message': 'Location deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def location_ajax_get(request, pk):
    """Get single location details for editing"""
    try:
        location = get_object_or_404(Location, pk=pk)
        data = {
            'id': location.id,
            'location_type_id': location.location_type.id if location.location_type else None,
            'name': location.name,
            'code': location.code,
            'manager_name': location.manager_name,
            'manager_email': location.manager_email,
            'manager_phone': location.manager_phone,
            'address_line1': location.address_line1,
            'address_line2': location.address_line2 or '',
            'city': location.city,
            'state': location.state,
            'country': str(location.country) if location.country else '',
            'postal_code': location.postal_code,
            'phone': location.phone,
            'working_hours': location.working_hours,
        }
        return JsonResponse({'success': True, 'location': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def location_ajax_update(request, pk):
    """Update location"""
    if request.method == "POST":
        try:
            location = get_object_or_404(Location, pk=pk)
            
            location.location_type_id = request.POST.get("location_type")
            location.name = request.POST.get("name")
            location.code = request.POST.get("code")
            location.manager_name = request.POST.get("manager_name")
            location.manager_email = request.POST.get("manager_email")
            location.manager_phone = request.POST.get("manager_phone")
            location.address_line1 = request.POST.get("address_line1")
            location.address_line2 = request.POST.get("address_line2")
            location.city = request.POST.get("city")
            location.state = request.POST.get("state")
            location.country = request.POST.get("country")
            location.postal_code = request.POST.get("postal_code")
            location.phone = request.POST.get("phone")
            location.working_hours = request.POST.get("working_hours")
            location.updated_by = request.user
            location.save()

            return JsonResponse({'success': True, 'message': 'Location updated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def company_setup_complete(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    messages.success(request, f"Company '{company.name}' has been set up successfully!")
    return redirect_with_company(request, "company_list")



#--------------------------------------------------------------------------------


"""
Company License Views 
company/views.py - License-related views with proper edit mode support
"""

from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
import traceback

from .models import Company
from company_settings.models import LicenseKey
from .constants import SYSTEM_MODULES, get_module_by_code
from .utils import generate_license_key, get_default_module_access
from company.erp_config import ERP_VERSION
from Lyraerp.utils.redirect_utils import redirect_with_company

# ========================================
# LICENSE CONFIGURATION (Company Setup)
# ========================================

@require_GET
@csrf_exempt
def get_license_configuration(request, company_id):
    """
     FIXED: Now properly returns existing license info for edit mode
    Returns:
    - license info (with all fields including activation details)
    - full system modules list
    - merged module access
    """
    try:
        # Get the most recent license for this company
        license_obj = LicenseKey.objects.filter(
            company_id=company_id
        ).order_by('-id').first()

        # =========================
        # BASE MODULE LIST (ALWAYS)
        # =========================
        modules = []
        default_access = get_default_module_access()

        for module in SYSTEM_MODULES:
            modules.append({
                "code": module["code"],
                "name": module["name"],
                "description": module.get("description", ""),
                "icon": module.get("icon", "bi-puzzle"),
                "is_core": module.get("is_core", False),
                "hasAccess": default_access.get(module["code"], False)
            })

        # =========================
        # NO LICENSE FOUND
        # =========================
        if not license_obj:
            print(f"ℹ️ No license found for company {company_id}")
            return JsonResponse({
                "success": True,
                "license": None,
                "modules": modules
            })

        # =========================
        # LICENSE EXISTS - Return Full Details
        # =========================
        is_expired = False
        days_remaining = 0

        if license_obj.expiry_date:
            delta = (license_obj.expiry_date - timezone.now().date()).days
            days_remaining = max(delta, 0)
            is_expired = delta < 0

        # Apply license module access to modules list
        license_access = license_obj.module_access or {}

        for m in modules:
            if m["is_core"]:
                m["hasAccess"] = True
            else:
                m["hasAccess"] = license_access.get(m["code"], False)

        #  FIXED: Return complete license information including activation details
        license_data = {
            "id": license_obj.id,
            "license_key": license_obj.license_key,
            "issue_date": license_obj.issue_date.strftime('%Y-%m-%d') if license_obj.issue_date else None,
            "expiry_date": license_obj.expiry_date.strftime('%Y-%m-%d') if license_obj.expiry_date else None,
            "is_active": license_obj.is_active,
            "is_expired": is_expired,
            "days_remaining": days_remaining,
            "company_id": license_obj.company_id,
            "company_gst": license_obj.company_gst or '',
            "company_pan": license_obj.company_pan or '',
            "max_users": license_obj.max_users,
            "max_locations": license_obj.max_locations,
            "erp_version": license_obj.erp_version or '1.0.0',
            "license_version": license_obj.license_version or 1,
            "notes": license_obj.notes or '',
            "module_access": license_access,
            #  NEW: Include activation metadata
            "activated_at": license_obj.activated_at.isoformat() if license_obj.activated_at else None,
            "activation_ip": license_obj.activation_ip or '',
        }

        print(f"✓ Returning license info for company {company_id}: {license_obj.license_key}")

        return JsonResponse({
            "success": True,
            "license": license_data,
            "modules": modules
        })

    except Exception as e:
        print(f"❌ Error in get_license_configuration: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


# ============================================================================
#  FIXED: Save License Configuration with Generator Confirmation
# ============================================================================

@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt
def save_license_configuration(request):
    """
    Save (create or update) license for a company.
    Expects JSON body with company_id, license_key, dates, module_access, etc.
    """
    
    print(f"\n{'='*80}")
    print(f"[LICENSE-SAVE-API] 🔵 ENDPOINT CALLED")
    print(f"{'='*80}")
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({'success': True})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        return response

    try:
        # --- Guard: empty body ---
        if not request.body:
            return JsonResponse({
                'success': False,
                'message': 'Empty request body. Expected JSON data.'
            }, status=400)

        # --- Parse JSON ---
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({
                'success': False,
                'message': f'Invalid JSON data: {str(e)}'
            }, status=400)

        company_id = data.get('company_id')
        license_key = data.get('license_key', '').strip()

        if not company_id:
            return JsonResponse({'success': False, 'message': 'company_id is required'}, status=400)
        if not license_key:
            return JsonResponse({'success': False, 'message': 'license_key is required'}, status=400)

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Company {company_id} not found'}, status=404)

        company_db = getattr(company, 'db_name', None) or request.session.get('company_db', 'default') or 'default'

        print(f"[LICENSE-SAVE-API] ✅ Parsed data: company_id={company_id}, license_key={license_key[:20]}..., company_db='{company_db}'")

        if company_db != 'default':
            try:
                from Lyraerp.utils.db_utils import register_database
                register_database(company_db)
                print(f"[LICENSE-SAVE-API] DB registered: {company_db}")
            except Exception as db_reg_err:
                print(f"[LICENSE-SAVE-API] ⚠️ Could not register DB '{company_db}': {db_reg_err}")
                company_db = 'default'

        try:
            company_in_db = Company.objects.using(company_db).get(pk=company_id)
        except Company.DoesNotExist:
            company_in_db = company

        issue_date_str = data.get('issue_date')
        expiry_date_str = data.get('expiry_date')
        max_users = data.get('max_users', 10)
        max_locations = data.get('max_locations', 5)
        company_gst = data.get('company_gst', '').strip()
        company_pan = data.get('company_pan', '').strip()
        is_active = data.get('is_active', True)
        erp_version = data.get('erp_version', '1.0.0')
        license_version = data.get('license_version', 1)
        notes = data.get('notes', '')

        module_access = data.get('module_access', {})
        if isinstance(module_access, str):
            try:
                module_access = json.loads(module_access)
            except Exception:
                module_access = {}
        if not module_access:
            module_access = get_default_module_access()

        if erp_version != ERP_VERSION:
            return JsonResponse({
                'success': False,
                'message': (
                    f"Version Mismatch: License is for ERP version {erp_version}, "
                    f"but you are running version {ERP_VERSION}. "
                    f"Please contact your vendor for a compatible license."
                )
            }, status=400)

        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                return None

        issue_date = parse_date(issue_date_str)
        expiry_date = parse_date(expiry_date_str)

        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        try:
                # ============== STEP 1: Create or update license record ==============
                with transaction.atomic(using=company_db):
                    license_obj, created = LicenseKey.objects.using(company_db).update_or_create(
                        company_id=company_id,
                        defaults={
                            'license_key': license_key,
                            'company_gst': company_gst,
                            'company_pan': company_pan,
                            'issue_date': issue_date,
                            'expiry_date': expiry_date,
                            'is_active': is_active,
                            'is_license_expired': False,  # CRITICAL: Set to False here
                            'max_users': max_users,
                            'max_locations': max_locations,
                            'module_access': module_access,
                            'erp_version': erp_version,
                            'license_version': license_version,
                            'notes': notes,
                            'activated_at': timezone.now(),
                            'activation_ip': ip_address,
                        }
                    )
                    # End of atomic block - transaction commits here
                
                # ============== STEP 2: Verify and force reset flag ==============
                # Do this AFTER transaction, with explicit DB commit
                reset_count = LicenseKey.objects.using(company_db).filter(
                    company_id=company_id
                ).update(
                    is_license_expired=False,
                    updated_at=timezone.now()
                )
                
                print(f"[LICENSE-SAVE] Step 2 reset: {reset_count} rows, company_db={company_db}, company_id={company_id}")
                logger.info(f"[LICENSE-SAVE] ✅ Set is_license_expired=False: {reset_count} rows affected in DB '{company_db}'")
                
                # ============== STEP 3: Verify from database ==============
                verify = LicenseKey.objects.using(company_db).filter(company_id=company_id).values(
                    'id', 'is_license_expired', 'expiry_date', 'is_active'
                ).first()
                
                if verify:
                    print(f"[LICENSE-SAVE] Step 3 verify: {verify}")
                    logger.info(f"[LICENSE-SAVE] DB verification: {verify}")
                
                # ============== STEP 4: Refresh the in-memory object ==============
                license_obj.refresh_from_db()
                print(f"[LICENSE-SAVE] Step 4 object: is_license_expired={license_obj.is_license_expired}")
                    
        except Exception as db_err:
            import traceback
            print(f"[LICENSE-SAVE] ERROR: {db_err}")
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': f'Database error: {str(db_err)}'}, status=500)

        action = "created" if created else "updated"
        days_remaining = 0
        if license_obj.expiry_date:
            days_remaining = (license_obj.expiry_date - timezone.now().date()).days

        print(f"[LICENSE-SAVE] Final response: is_license_expired={license_obj.is_license_expired}, days_remaining={days_remaining}")
        
        return JsonResponse({
            'success': True,
            'message': f'License {action} successfully',
            'license': {
                'id': license_obj.id,
                'license_key': license_obj.license_key,
                'company_gst': license_obj.company_gst,
                'company_pan': license_obj.company_pan,
                'issue_date': license_obj.issue_date.isoformat() if license_obj.issue_date else None,
                'expiry_date': license_obj.expiry_date.isoformat() if license_obj.expiry_date else None,
                'is_active': license_obj.is_active,
                'is_expired': False,
                'is_license_expired': license_obj.is_license_expired,  # DEBUG
                'max_users': license_obj.max_users,
                'max_locations': license_obj.max_locations,
                'module_access': license_obj.module_access,
                'erp_version': license_obj.erp_version,
                'license_version': license_obj.license_version,
                'days_remaining': days_remaining,
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Unexpected error: {str(e)}'}, status=500)
        
# ========================================
# LICENSE VALIDATION
# ========================================

@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt
def validate_license_key(request):
    """
    Validate license key from generator API first, then local database
    This allows validating NEW/RENEWED licenses that aren't in ERP yet
    """
    try:
        data = json.loads(request.body)
        license_key = data.get('license_key', '').strip()
        company_id = data.get('company_id')
        company_name = data.get('company_name', '').strip()
        company_gst = data.get('company_gst', '').strip()
        erp_version = data.get('erp_version', '1.0.0')
        erp_confirmed = data.get('erp_confirmed', False)
        
        print(f"🔍 Validating license key: {license_key}")
        print(f"   Company ID: {company_id}")
        print(f"   Company Name: {company_name}")
        print(f"   Company GST: {company_gst}")
        print(f"   ERP Confirmed: {erp_confirmed}")
        
        if not license_key:
            return JsonResponse({
                'success': False,
                'message': 'License key is required'
            }, status=400)
        
        # PHASE 1: Check generator API first (for new/renewed licenses)
        GENERATOR_API_URL = f"{settings.LICENSE_GENERATOR_API_URL}/api/activate/"
        
        try:
            print(f"📤 Calling generator API: {GENERATOR_API_URL}")
            
            generator_payload = {
                'license_key': license_key,
                'company_id': company_id,
                'company_name': company_name,
                'company_gst': company_gst,
                'erp_version': erp_version,
                'erp_confirmed': erp_confirmed
            }
            
            response = requests.post(
                GENERATOR_API_URL,
                json=generator_payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            print(f"📥 Generator API response status: {response.status_code}")
            
            if response.status_code == 200:
                generator_data = response.json()
                print(f"✓ Generator API response: {generator_data}")
                
                if generator_data.get('success'):
                    license_info = generator_data.get('license', {})
                    
                    # Calculate days remaining
                    expiry_date_str = license_info.get('expiry_date')
                    days_remaining = 0
                    
                    if expiry_date_str:
                        try:
                            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00')).date()
                            days_remaining = (expiry_date - timezone.now().date()).days
                        except:
                            pass
                    
                    return JsonResponse({
                        'success': True,
                        'is_valid': True,
                        'license': {
                            'license_key': license_info.get('license_key'),
                            'company_name': license_info.get('company_name'),
                            'company_gst': license_info.get('company_gst'),
                            'company_pan': license_info.get('company_pan'),
                            'issue_date': license_info.get('issue_date'),
                            'expiry_date': license_info.get('expiry_date'),
                            'max_users': license_info.get('max_users'),
                            'max_locations': license_info.get('max_locations'),
                            'module_access': license_info.get('module_access', {}),
                            'erp_version': license_info.get('erp_version'),
                            'license_version': license_info.get('license_version'),
                            'is_expired': days_remaining < 0,
                            'days_remaining': max(days_remaining, 0)
                        },
                        'source': 'generator',
                        'message': 'License validated from generator'
                    })
                else:
                    # Generator returned error
                    return JsonResponse({
                        'success': False,
                        'is_valid': False,
                        'message': generator_data.get('message', 'License validation failed'),
                        'source': 'generator'
                    })
            else:
                print(f"⚠️ Generator API returned status {response.status_code}")
                # Fall through to check local database
                
        except requests.exceptions.Timeout:
            print("⚠️ Generator API timeout - falling back to local database")
        except requests.exceptions.ConnectionError:
            print("⚠️ Generator API connection error - falling back to local database")
        except Exception as api_error:
            print(f"⚠️ Generator API error: {str(api_error)}")
            traceback.print_exc()
        
        # PHASE 2: Fallback to local ERP database (for existing licenses)
        print("🔍 Checking local ERP database...")
        
        try:
            license_obj = LicenseKey.objects.get(license_key=license_key)
            
            is_valid = license_obj.is_active and not license_obj.is_expired()
            
            return JsonResponse({
                'success': True,
                'is_valid': is_valid,
                'license': {
                    'license_key': license_obj.license_key,
                    'company_name': license_obj.company.name,
                    'company_gst': license_obj.company_gst,
                    'company_pan': license_obj.company_pan,
                    'issue_date': license_obj.issue_date.isoformat() if license_obj.issue_date else None,
                    'expiry_date': license_obj.expiry_date.isoformat() if license_obj.expiry_date else None,
                    'max_users': license_obj.max_users,
                    'max_locations': license_obj.max_locations,
                    'module_access': license_obj.module_access or {},
                    'erp_version': license_obj.erp_version,
                    'license_version': license_obj.license_version,
                    'is_expired': license_obj.is_expired(),
                    'days_remaining': license_obj.days_remaining()
                },
                'source': 'database',
                'message': 'License found in local database' if is_valid else 'License is expired or inactive'
            })
            
        except LicenseKey.DoesNotExist:
            return JsonResponse({
                'success': False,
                'is_valid': False,
                'message': 'Invalid license key - not found in generator or local database',
                'source': 'none'
            })
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error validating license: {str(e)}'
        }, status=500)

# ============================================================================
# Check Module Access
# ============================================================================
@require_http_methods(["GET"])
def check_module_access(request, company_id, module_code):
    """
    Check if a company has access to a specific module.
    """
    try:
        company = get_object_or_404(Company, pk=company_id)
        
        try:
            license_obj = LicenseKey.objects.get(company=company)
            
            if not license_obj.is_active:
                return JsonResponse({
                    'success': False,
                    'has_access': False,
                    'message': 'License is not active'
                })
            
            if license_obj.is_expired():
                return JsonResponse({
                    'success': False,
                    'has_access': False,
                    'message': 'License has expired'
                })
            
            has_access = license_obj.has_module_access(module_code)
            
            return JsonResponse({
                'success': True,
                'has_access': has_access,
                'module_code': module_code,
                'license_status': license_obj.get_status_display()
            })
            
        except LicenseKey.DoesNotExist:
            module = get_module_by_code(module_code)
            is_core = module.get('is_core', False) if module else False
            
            return JsonResponse({
                'success': True,
                'has_access': is_core,
                'message': 'No license found - only core modules accessible'
            })
            
    except Company.DoesNotExist:
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': 'Company not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': str(e)
        }, status=500)


# ========================================
# LICENSE ERROR PAGES
# ========================================


@login_required
def license_expired(request):
    """
    Show when company license has expired
    """
    license_info = getattr(request, 'license_info', {})
    expiry_date = license_info.get('expiry_date')
    
    context = {
        'title': 'License Expired',
        'message': 'Your company\'s license has expired.',
        'sub_message': 'Please renew your license to continue using the system.',
        'expiry_date': expiry_date,
        'company_name': request.session.get('company_name', 'your company'),
    }
    return render(request, 'company/license_expired.html', context, status=403)


@login_required
def license_required(request):
    """
    Show when company has no valid license key
    """
    context = {
        'title': 'License Required',
        'message': 'Your company does not have a valid license key.',
        'sub_message': 'Please contact your administrator to activate a license.',
        'company_name': request.session.get('company_name', 'your company'),
    }
    return render(request, 'company/license_required.html', context, status=403)


@login_required
def module_not_allowed(request):
    """
    Show when user tries to access a module not included in their license
    """
    license_info = getattr(request, 'license_info', {})
    allowed_modules = license_info.get('allowed_modules', [])
    
    context = {
        'title': 'Module Not Allowed',
        'message': 'This module is not included in your license.',
        'sub_message': 'Please upgrade your license to access this module.',
        'allowed_modules': allowed_modules,
        'company_name': request.session.get('company_name', 'your company'),
    }
    return render(request, 'company/module_not_allowed.html', context, status=403)


# ========================================
# HELPER FUNCTIONS (Can be in utils.py)
# ========================================

def get_company_license_info(company):
    """
    Helper function to get license info for a company
    Returns dict with license status
    """
    try:
        license_obj = LicenseKey.objects.get(company=company)
        
        return {
            'exists': True,
            'is_active': license_obj.is_active,
            'is_expired': license_obj.is_expired(),
            'days_remaining': license_obj.days_remaining(),
            'expiry_date': license_obj.expiry_date,
            'license_key': license_obj.license_key,
            'max_users': license_obj.max_users,
            'enabled_modules': license_obj.get_enabled_modules(),
            'warning': license_obj.get_expiry_warning(),
        }
    except LicenseKey.DoesNotExist:
        return {
            'exists': False,
            'is_active': False,
            'is_expired': True,
            'days_remaining': 0,
        }


def check_license_and_module(company, module_code):
    """
    Check if company has valid license and module access
    Returns: (has_access: bool, reason: str)
    """
    try:
        license_obj = LicenseKey.objects.get(company=company)
        
        if not license_obj.is_active:
            return False, "License is inactive"
        
        if license_obj.is_expired():
            return False, "License has expired"
        
        if not license_obj.has_module_access(module_code):
            return False, "Module not enabled in license"
        
        return True, "Access granted"
        
    except LicenseKey.DoesNotExist:
        return False, "No license found"




@login_required
def license_restricted_view(request):
    """
    Show the license restriction page when user doesn't have a valid license.
    """
    # Get license info from request (set by middleware)
    license_info = getattr(request, 'license_info', {})
    company_id = getattr(request, 'company_id', None)
    
    context = {
        'license_info': license_info,
        'company_id': company_id,
    }
    
    return render(request, 'company/license_expired.html', context)




@login_required
def trial_expired_page(request):
    """
    Dedicated trial-expired endpoint.
    Returns 403 while keeping URL as /<company_code>/trial-expired/.
    """
    license_info = getattr(request, 'license_info', {})
    company_id = getattr(request, 'company_id', None)
    company_code = getattr(request, 'company_code', None)

    context = {
        'license_info': license_info,
        'company_id': company_id,
        'company_code': company_code,
        'contact_email': 'lyraerp@techlyra.com',
    }
    # Render as 200 to avoid "Forbidden" server logs while still showing
    # the trial-expired screen. Access blocking is enforced by middleware.
    return render(request, 'trial_expired.html', context, status=200)


@login_required
def site_blocked_view(request):
    """
    Display the site access restricted page.
    This view renders your existing site_blocked.html template.
    """
    # Get license info from request (set by middleware)
    license_info = getattr(request, 'license_info', {})
    company_id = getattr(request, 'company_id', None)
    
    context = {
        'license_info': license_info,
        'company_id': company_id,
        'company_code': getattr(request, 'company_code', None),
        'contact_email': 'lyraerp@techlyra.com',
    }
    
    # Render your existing template
    return render(request, 'site_blocked.html', context)




# company/views.py - License Activation View
"""
License Activation View - Complete Integration
==============================================

This view handles license activation for companies in trial or without licenses.
Integrates with:
- Existing LicenseKey model from company_settings
- License generator API for validation
- Trial system for automatic trial deactivation
- ERP version validation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from datetime import datetime
import requests
import json
import logging
import traceback

from company.models import Company
from company_settings.models import LicenseKey
from company.erp_config import ERP_VERSION
from Lyraerp.utils.redirect_utils import redirect_with_company

logger = logging.getLogger(__name__)


@login_required
def activate_license(request, company_code=None):
    """
    View to activate a license key.
    
    Features:
    - Validates license key with generator API
    - Checks ERP version compatibility
    - Creates/updates LicenseKey record
    - Deactivates trial mode if active
    - Accessible even with expired trial
    - Can be accessed from company_code in URL or session
    
    Flow:
    1. User enters license key
    2. Validate with generator API
    3. Check ERP version compatibility
    4. Save to LicenseKey model
    5. Deactivate trial
    6. Redirect to dashboard
    """
    
    # ============================================
    # STEP 1: Get company information
    # ============================================
    company_id = request.session.get('company_id')
    company = None
    
    # Try to get from session first
    if company_id:
        try:
            company = Company.objects.using('default').get(id=company_id)
            logger.info(f"[LICENSE ACTIVATION] Found company from session: {company.name} (ID: {company_id})")
        except Company.DoesNotExist:
            company = None
    
    # If not in session, try to get from company_code in URL
    if not company and company_code:
        try:
            company = Company.objects.using('default').get(company_code=company_code)
            logger.info(f"[LICENSE ACTIVATION] Found company from URL: {company.name} (code: {company_code})")
            company_id = company.id
            # Set in session for consistency
            request.session['company_id'] = company_id
            request.session.modified = True
        except Company.DoesNotExist:
            company = None
    
    # If still not found, try to get from authenticated user's role
    if not company and request.user.is_authenticated:
        try:
            from user.models import User as CustomUser
            custom_user = CustomUser.objects.using('default').filter(
                usr_name=request.user.username
            ).select_related('usr_roleid__company').first()
            
            if custom_user and custom_user.usr_roleid and custom_user.usr_roleid.company:
                company = custom_user.usr_roleid.company
                company_id = company.id
                logger.info(f"[LICENSE ACTIVATION] Found company from user role: {company.name}")
                # Set in session for consistency
                request.session['company_id'] = company_id
                request.session.modified = True
        except Exception as e:
            logger.warning(f"[LICENSE ACTIVATION] Error getting company from user: {e}")
    
    # If still no company found, redirect to login
    if not company or not company_id:
        messages.error(request, "No company found. Please login first.")
        logger.error("[LICENSE ACTIVATION] No company found from session, URL, or user role")
        return redirect_with_company('login')
    
    logger.info(f"[LICENSE ACTIVATION] Using company: {company.name} (ID: {company_id})")
    
    # ============================================
    # STEP 2: Get company database for license storage
    # ============================================
    company_db = request.session.get('company_db', company.db_name or 'default')
    logger.debug(f"[LICENSE ACTIVATION] Using database: {company_db}")
    
    # ============================================
    # STEP 3: Check if license already exists
    # ============================================
    existing_license = None
    try:
        existing_license = LicenseKey.objects.using(company_db).filter(
            company=company
        ).order_by('-id').first()
        
        if existing_license:
            logger.info(
                f"[LICENSE ACTIVATION] Existing license found: "
                f"{existing_license.license_key} "
                f"(Active: {existing_license.is_active}, "
                f"Expired: {existing_license.is_expired() if hasattr(existing_license, 'is_expired') else 'N/A'})"
            )
    except Exception as e:
        logger.warning(f"[LICENSE ACTIVATION] Error checking existing license: {e}")
    
    # ============================================
    # STEP 4: Handle form submission
    # ============================================
    if request.method == 'POST':
        license_key = request.POST.get('license_key', '').strip()
        logger.info(f"[LICENSE ACTIVATION] POST received for company {company.name}")
        logger.debug(f"[LICENSE ACTIVATION] License key submitted: {license_key[:10]}..." if license_key else "[LICENSE ACTIVATION] Empty license key")
        
        if not license_key:
            messages.error(request, "Please enter a license key")
            logger.warning("[LICENSE ACTIVATION] Empty license key submitted")
        else:
            # Process license activation
            success, message, license_data = _process_license_activation(
                license_key, 
                company, 
                company_db,
                request
            )
            
            if success:
                messages.success(request, message)
                logger.info(f"[LICENSE ACTIVATION] ✅ License activated successfully for {company.name}")
                
                # Refresh company from database to get updated trial_active status
                try:
                    company = Company.objects.using('default').get(id=company.id)
                    logger.info(f"[LICENSE ACTIVATION] ✅ Refreshed company data: trial_active={company.trial_active}")
                except Exception as e:
                    logger.warning(f"[LICENSE ACTIVATION] Could not refresh company data: {e}")
                
                # Redirect to dashboard
                final_company_code = company_code or company.company_code
                if final_company_code:
                    redirect_url = f'/{final_company_code}/'
                    logger.info(f"[LICENSE ACTIVATION] ✅ SUCCESS! Redirecting to {redirect_url}")
                    logger.info(f"[LICENSE ACTIVATION] Company: {company.name}")
                    logger.info(f"[LICENSE ACTIVATION] trial_active: {company.trial_active}")
                    logger.info(f"[LICENSE ACTIVATION] license activated: {success}")
                    return redirect_with_company(redirect_url)
                logger.warning(f"[LICENSE ACTIVATION] No company_code available, redirecting to index")
                return redirect_with_company('index')
            else:
                messages.error(request, message)
                logger.warning(f"[LICENSE ACTIVATION] ❌ Failed for {company.name}: {message}")
    
    # ============================================
    # STEP 5: Get trial summary for display
    # ============================================
    trial_summary = None
    try:
        from company.utils.trial_utils import get_trial_summary
        trial_summary = get_trial_summary(company)
        logger.debug(f"[LICENSE ACTIVATION] Trial summary: {trial_summary}")
    except ImportError:
        logger.warning("[LICENSE ACTIVATION] trial_utils not available")
        # Fallback trial info
        trial_summary = {
            'status': 'unknown',
            'message': 'Trial status unknown',
            'is_expired': company.check_trial_expired() if hasattr(company, 'check_trial_expired') else False,
            'days_remaining': company.days_until_trial_expires() if hasattr(company, 'days_until_trial_expires') else None,
        }
    except Exception as e:
        logger.error(f"[LICENSE ACTIVATION] Error getting trial summary: {e}")
        trial_summary = {'status': 'error', 'message': 'Error loading trial status'}
    
    # ============================================
    # STEP 6: Prepare context and render template
    # ============================================
    context = {
        'company': company,
        'trial_summary': trial_summary,
        'existing_license': existing_license,
        'erp_version': ERP_VERSION,
    }
    
    return render(request, 'company/activate_license.html', context)


# ============================================================================
# Helper Function: Process License Activation
# ============================================================================
def _process_license_activation(license_key, company, company_db, request):
    """
    Phase 1: validate with generator, phase 2: save, phase 3: confirm.
    """
    import json, requests, traceback
    from django.conf import settings
    from company.erp_config import ERP_VERSION

    logger.info("[LICENSE ACTIVATION] Processing: company=%s key=%s", company.name, license_key)

    generator_api_url = f"{settings.LICENSE_GENERATOR_API_URL}/api/activate/"

    # ── Phase 1: validate (erp_confirmed=False) ─────────────────────────────
    try:
        payload = {
            'license_key':  license_key,
            'company_id':   company.id,
            'company_name': company.name,
            'company_gst':  company.tax_id or '',
            'erp_version':  ERP_VERSION,
            'erp_confirmed': False,
        }
        logger.info("[LICENSE ACTIVATION] Phase 1 POST → %s", generator_api_url)
        response = requests.post(
            generator_api_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        logger.info("[LICENSE ACTIVATION] Phase 1 status: %s", response.status_code)

        if response.status_code != 200:
            try:
                msg = response.json().get('message', f'HTTP {response.status_code}')
            except Exception:
                msg = f'Generator returned HTTP {response.status_code}'
            return False, msg, None

        api_data = response.json()
        logger.info("[LICENSE ACTIVATION] Phase 1 raw response: %s",
                    json.dumps(api_data, default=str))

        if not api_data.get('success'):
            return False, api_data.get('message', 'License validation failed'), None

        license_info = api_data.get('license', {})

        # Version guard
        license_erp_version = license_info.get('erp_version', '')
        if license_erp_version != ERP_VERSION:
            msg = (
                f"Version Mismatch: License is for ERP {license_erp_version}, "
                f"but you are running {ERP_VERSION}. "
                f"Contact your vendor for a compatible license."
            )
            logger.error("[LICENSE ACTIVATION] %s", msg)
            return False, msg, None

        logger.info("[LICENSE ACTIVATION] Phase 1 ✅ version OK")

    except requests.exceptions.Timeout:
        return False, "License server timed out. Please try again.", None
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to license server. Check your network.", None
    except Exception as exc:
        logger.error("[LICENSE ACTIVATION] Phase 1 error: %s", exc)
        return False, f"Error contacting license server: {str(exc)}", None

    # ── Phase 2: save to ERP database ───────────────────────────────────────
    saved, message = _save_license_to_database(
        license_key, license_info, company, company_db, request
    )
    if not saved:
        return False, message, None

    # ── Phase 3: confirm with generator (fire-and-forget) ───────────────────
    try:
        requests.post(
            generator_api_url,
            json={
                'license_key':  license_key,
                'company_id':   company.id,
                'company_name': company.name,
                'company_gst':  company.tax_id or '',
                'erp_version':  ERP_VERSION,
                'erp_confirmed': True,
            },
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        logger.info("[LICENSE ACTIVATION] Phase 3 ✅ confirmation sent")
    except Exception as exc:
        logger.warning("[LICENSE ACTIVATION] Phase 3 confirmation failed (non-fatal): %s", exc)

    # ── Deactivate trial ─────────────────────────────────────────────────────
    try:
        if company.trial_active:
            company.trial_active = False
            Company.objects.using('default').filter(pk=company.pk).update(trial_active=False)
            logger.info("[LICENSE ACTIVATION] Trial deactivated in master DB")
            if hasattr(company, '_sync_fields_to_company_db'):
                company._sync_fields_to_company_db(['trial_active'])
    except Exception as exc:
        logger.error("[LICENSE ACTIVATION] Error deactivating trial: %s", exc)

    return True, message, license_info


# ============================================================================
# Helper Function: Save License to Database
# ============================================================================
def _save_license_to_database(license_key, license_info, company, company_db, request):
    """
    Persist license data to LicenseKey model.

    FIX: previously company_gst, company_pan, module_access, max_users,
    max_locations were never read from license_info — now they are.
    """
    import json, traceback
    from datetime import datetime
    from django.db import transaction
    from django.utils import timezone
    from company_settings.models import LicenseKey
    from company.erp_config import ERP_VERSION

    try:
        logger.info("[LICENSE ACTIVATION] Phase 2 saving to DB '%s'", company_db)
        logger.info("[LICENSE ACTIVATION] Raw license_info: %s",
                    json.dumps(license_info, default=str))

        # ── Date parsing ────────────────────────────────────────────────────
        def _parse(date_str):
            if not date_str:
                return None
            try:
                return datetime.fromisoformat(
                    str(date_str).replace('Z', '+00:00')
                ).date()
            except (ValueError, AttributeError) as exc:
                logger.warning("[LICENSE ACTIVATION] Cannot parse date '%s': %s", date_str, exc)
                return None

        issue_date  = _parse(license_info.get('issue_date'))
        expiry_date = _parse(license_info.get('expiry_date'))

        # ── Numeric fields ───────────────────────────────────────────────────
        def _safe_int(val, default):
            try:
                result = int(val or 0)
                return result if result > 0 else default
            except (TypeError, ValueError):
                return default

        max_users     = _safe_int(license_info.get('max_users'),     10)
        max_locations = _safe_int(license_info.get('max_locations'),  5)

        # ── Text fields ──────────────────────────────────────────────────────
        company_gst = str(license_info.get('company_gst') or '').strip()
        company_pan = str(license_info.get('company_pan') or '').strip()

        # ── Module access ────────────────────────────────────────────────────
        raw_modules = license_info.get('module_access', {})
        if isinstance(raw_modules, str):
            try:
                raw_modules = json.loads(raw_modules)
            except Exception:
                raw_modules = {}
        if isinstance(raw_modules, (list, tuple)):
            raw_modules = {str(code): True for code in raw_modules}
        if isinstance(raw_modules, dict):
            normalized_modules = {str(k): bool(v) for k, v in raw_modules.items()}
        else:
            normalized_modules = {}

        # ── IP address ───────────────────────────────────────────────────────
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR',
                                      request.META.get('REMOTE_ADDR', ''))
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        logger.info(
            "[LICENSE ACTIVATION] Values → gst='%s' pan='%s' "
            "issue=%s expiry=%s users=%s locs=%s modules=%s",
            company_gst, company_pan, issue_date, expiry_date,
            max_users, max_locations, normalized_modules,
        )

        # ── Fetch company row from target DB ─────────────────────────────────
        try:
            company_in_db = Company.objects.using(company_db).get(pk=company.pk)
        except Exception:
            company_in_db = company
            logger.warning(
                "[LICENSE ACTIVATION] Could not fetch company from '%s', "
                "using passed instance", company_db
            )

        # ── Write ────────────────────────────────────────────────────────────
        with transaction.atomic(using=company_db):
            license_obj, created = LicenseKey.objects.using(company_db).update_or_create(
                company=company_in_db,
                defaults={
                    'license_key':     license_key,
                    'company_gst':     company_gst,
                    'company_pan':     company_pan,
                    'issue_date':      issue_date,
                    'expiry_date':     expiry_date,
                    'is_active':       True,
                    'is_license_expired': False,  # 🔥 CRITICAL: Reset expired flag on activation!
                    'max_users':       max_users,
                    'max_locations':   max_locations,
                    'module_access':   normalized_modules,
                    'erp_version':     license_info.get('erp_version', ERP_VERSION),
                    'license_version': _safe_int(license_info.get('license_version'), 1),
                    'notes':           str(license_info.get('notes', '') or ''),
                    'activated_at':    timezone.now(),
                    'activation_ip':   ip_address,
                },
            )
        
        # 🔥 EXPLICIT FORCE-RESET: Ensure flag is definitely False
        # Critical for renewals where the flag was previously True
        reset_count = LicenseKey.objects.using(company_db).filter(
            company_id=company_in_db.pk
        ).update(is_license_expired=False)
        logger.info(
            "[LICENSE ACTIVATION] Force-reset is_license_expired=False: %d rows affected",
            reset_count,
        )

        action = "activated" if created else "updated"
        logger.info(
            "[LICENSE ACTIVATION] ✅ License %s: id=%s gst=%s pan=%s "
            "issue=%s expiry=%s users=%s locs=%s modules=%s is_license_expired=False",
            action, license_obj.id,
            license_obj.company_gst, license_obj.company_pan,
            license_obj.issue_date, license_obj.expiry_date,
            license_obj.max_users, license_obj.max_locations,
            license_obj.module_access,
        )

        days_remaining = "unlimited"
        if expiry_date:
            delta = (expiry_date - timezone.now().date()).days
            days_remaining = f"{delta} days" if delta > 0 else "expired"

        message = (
            f"License {action} successfully! "
            f"Valid until: {expiry_date.strftime('%B %d, %Y') if expiry_date else 'No expiry'} "
            f"({days_remaining})"
        )
        return True, message

    except Exception as exc:
        logger.error("[LICENSE ACTIVATION] Phase 2 DB error: %s", exc)
        logger.error(traceback.format_exc())
        return False, f"Error saving license: {str(exc)}"

# ============================================================================
# AJAX Endpoint: Validate License Key (for real-time validation in form)
# ============================================================================

@require_http_methods(["POST", "OPTIONS"])
@login_required
def ajax_validate_license_key(request):
    """
    AJAX endpoint to validate license key in real-time.
    
    Returns:
        JSON with validation result and license info
    """
    try:
        data = json.loads(request.body)
        license_key = data.get('license_key', '').strip()
        
        if not license_key:
            return JsonResponse({
                'success': False,
                'message': 'License key is required'
            }, status=400)
        
        # Get company info
        company_id = request.session.get('company_id')
        if not company_id:
            return JsonResponse({
                'success': False,
                'message': 'No company found in session'
            }, status=400)
        
        company = Company.objects.using('default').get(id=company_id)
        
        # Validate with generator API
        generator_api_url = f"{settings.LICENSE_GENERATOR_API_URL}/api/activate/"
        
        payload = {
            'license_key': license_key,
            'company_id': company.id,
            'company_name': company.name,
            'company_gst': company.tax_id or '',
            'erp_version': ERP_VERSION,
            'erp_confirmed': False,  # Just validating, not activating yet
        }
        
        response = requests.post(
            generator_api_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            api_data = response.json()
            
            if api_data.get('success'):
                license_info = api_data.get('license', {})
                
                # Check ERP version
                license_erp_version = license_info.get('erp_version', '1.0.0')
                version_match = license_erp_version == ERP_VERSION
                
                return JsonResponse({
                    'success': True,
                    'is_valid': True,
                    'version_match': version_match,
                    'license': {
                        'company_name': license_info.get('company_name'),
                        'expiry_date': license_info.get('expiry_date'),
                        'max_users': license_info.get('max_users'),
                        'max_locations': license_info.get('max_locations'),
                        'erp_version': license_erp_version,
                    },
                    'message': 'Valid license key' if version_match else f'Version mismatch: License is for v{license_erp_version}, you are running v{ERP_VERSION}'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'is_valid': False,
                    'message': api_data.get('message', 'Invalid license key')
                })
        else:
            return JsonResponse({
                'success': False,
                'is_valid': False,
                'message': 'License validation failed'
            })
    
    except Exception as e:
        logger.error(f"[AJAX LICENSE VALIDATION] Error: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
