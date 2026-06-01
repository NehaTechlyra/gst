from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone

from Lyraerp.utils.redirect_utils import redirect_with_company

from company.models import Company

from .models import Currency, ExchangeRate


def _currency_display_defaults(code):
    code = (code or "").strip().upper()[:3]
    try:
        from currencies.utils import get_currency_symbol, get_currency_name

        symbol = get_currency_symbol(code) or code
        name = get_currency_name(code) or code
    except Exception:
        symbol = code
        name = code
    return symbol, name


def _repair_currency_display_values(currency_qs, company_id):
    for cur in currency_qs.filter(company_id=company_id, is_active=True):
        code = (cur.code or "").strip().upper()[:3]
        if not code:
            continue
        updates = {}
        if not cur.symbol or cur.symbol.strip().upper() == code:
            updates["symbol"] = _currency_display_defaults(code)[0]
        if not cur.name or cur.name.strip().upper() == code:
            updates["name"] = _currency_display_defaults(code)[1]
        if updates:
            currency_qs.filter(pk=cur.pk).update(**updates)


def _sync_company_base_currency(company, code):
    code = (code or "").strip().upper()[:3]
    company_db = getattr(company, "db_name", None) or getattr(company._state, "db", None)
    Company.objects.using("default").filter(pk=company.pk).update(base_currency=code)
    if company_db and company_db != "default":
        try:
            Company.objects.using(company_db).filter(pk=company.pk).update(base_currency=code)
        except Exception:
            pass
    company.base_currency = code


def _company_for_request(request):
    company_code = getattr(request, "company_code", None) or (
        request.session.get("company_code") if hasattr(request, "session") else None
    )
    company_db = getattr(request, "company_db", None) or (
        request.session.get("company_db") if hasattr(request, "session") else None
    )
    cid = request.session.get("company_id") if hasattr(request, "session") else None

    if company_db and company_db != "default":
        qs = Company.objects.using(company_db)
        if company_code:
            company = qs.filter(company_code=company_code).first()
            if company:
                return company
        if cid:
            company = qs.filter(pk=cid).first()
            if company:
                return company
        company = qs.order_by("id").first()
        if company:
            return company

    qs = Company.objects.using("default")
    if company_code:
        company = qs.filter(company_code=company_code).first()
        if company:
            return company
    if cid:
        company = qs.filter(pk=cid).first()
        if company:
            return company
    return qs.order_by("id").first()




def _currency_qs(company):
    from django.db import connections
    from Lyraerp.utils.db_utils import register_database
    from Lyraerp.utils.thread_locals import get_current_db

    db_name = get_current_db()
    if not db_name or db_name == "default":
        db_name = getattr(company, "db_name", None)
    if not db_name:
        return None
    if db_name not in connections.databases:
        try:
            register_database(db_name)
        except Exception:
            return None
    return Currency.objects.using(db_name)


def _exchange_rate_qs(company):
    from django.db import connections
    from Lyraerp.utils.db_utils import register_database
    from Lyraerp.utils.thread_locals import get_current_db

    db_name = get_current_db()
    if not db_name or db_name == "default":
        db_name = getattr(company, "db_name", None)
    if not db_name:
        return None
    if db_name not in connections.databases:
        try:
            register_database(db_name)
        except Exception:
            return None
    return ExchangeRate.objects.using(db_name)


@login_required
def currency_list(request):
    company = _company_for_request(request)
    if not company:
        messages.error(request, "No organisation found.")
        return redirect_with_company(request, "website:index")

    qs = _currency_qs(company)
    if qs is None:
        qs = Currency.objects.none()
    else:
        qs = qs.filter(company_id=company.pk).order_by("-is_base", "code")
    has_base = False
    if _currency_qs(company) is not None:
        currency_qs = _currency_qs(company)
        base_currency = currency_qs.filter(company_id=company.pk, is_base=True).order_by("id").first()
        has_base = bool(base_currency)
        if base_currency and not (company.base_currency or "").strip():
            Company.objects.using("default").filter(pk=company.pk).update(base_currency=base_currency.code)
            company.base_currency = base_currency.code
        _repair_currency_display_values(currency_qs, company.pk)
    return render(
        request,
        "currencies/currency_list.html",
        {
            "currencies": qs,
            "company": company,
            "has_base_currency": has_base,
        },
    )


@login_required
def currency_add(request):
    company = _company_for_request(request)
    if not company:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "No organisation found."}, status=400)
        messages.error(request, "No organisation found.")
        return redirect_with_company(request, "website:index")

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().upper()[:3]
        symbol = (request.POST.get("symbol") or "").strip()[:8]
        name = (request.POST.get("name") or "").strip()[:80]
        try:
            decimals = int(request.POST.get("decimal_places") or 2)
        except ValueError:
            decimals = 2
        decimals = max(0, min(6, decimals))
        display_format = request.POST.get("display_format") or "1,234.56"
        if display_format not in dict(Currency.FORMAT_CHOICES):
            display_format = "1,234.56"
        is_base = request.POST.get("is_base") == "on"
        if not code:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Currency code is required."}, status=400)
            messages.error(request, "Currency code is required.")
        else:
            default_symbol, default_name = _currency_display_defaults(code)
            currency_qs = _currency_qs(company)
            if currency_qs is None:
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "Company database is not configured."}, status=400)
                messages.error(request, "Company database is not configured.")
                return redirect_with_company(request, "website:index")
            with transaction.atomic():
                if is_base:
                    currency_qs.filter(company_id=company.pk, is_base=True).update(is_base=False)
                    _sync_company_base_currency(company, code)
                cur, _created = currency_qs.update_or_create(
                    company_id=company.pk,
                    code=code,
                    defaults={
                        "symbol": symbol or default_symbol,
                        "name": name or default_name,
                        "decimal_places": decimals,
                        "display_format": display_format,
                        "is_base": is_base,
                        "is_active": True,
                    },
                )
                if is_base:
                    currency_qs.filter(company_id=company.pk, is_base=True).exclude(pk=cur.pk).update(is_base=False)
                    if not cur.is_base:
                        cur.is_base = True
                        cur.save(update_fields=["is_base"])
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "id": cur.pk,
                        "code": cur.code,
                        "name": cur.name,
                        "symbol": cur.symbol,
                        "is_base": cur.is_base,
                        "display": cur.code,
                    }
                )
            messages.success(request, f"Currency {code} saved.")
            return redirect_with_company(request, "currencies:currency_list")

    return render(
        request,
        "currencies/currency_form.html",
        {"title": "Add currency", "company": company, "format_choices": Currency.FORMAT_CHOICES},
    )


@login_required
def currency_edit(request, pk):
    company = _company_for_request(request)
    currency_qs = _currency_qs(company)
    if currency_qs is None:
        messages.error(request, "Company database is not configured.")
        return redirect_with_company(request, "currencies:currency_list")
    cur = get_object_or_404(currency_qs.filter(company_id=company.pk), pk=pk)
    if request.method == "POST":
        symbol = (request.POST.get("symbol") or "").strip()[:8]
        name = (request.POST.get("name") or "").strip()[:80]
        try:
            decimals = int(request.POST.get("decimal_places") or 2)
        except ValueError:
            decimals = 2
        decimals = max(0, min(6, decimals))
        display_format = request.POST.get("display_format") or "1,234.56"
        if display_format not in dict(Currency.FORMAT_CHOICES):
            display_format = "1,234.56"
        is_base = request.POST.get("is_base") == "on"
        with transaction.atomic():
            # Setting this currency as base
            if is_base and not cur.is_base:
                currency_qs.filter(company_id=company.pk, is_base=True).update(is_base=False)
                _sync_company_base_currency(company, cur.code)


            # Unsetting base on the current currency (user unchecked the base flag)
            if (not is_base) and cur.is_base:
                # Prevent unsetting base if this currency is referenced by transactions or rates
                usage_msgs = []
                try:
                    from sales.models import SalesInvoice
                    if SalesInvoice.objects.using(getattr(company, "db_name", "default")).filter(document_currency=cur).exists():
                        usage_msgs.append('sales invoices')
                except Exception:
                    pass
                try:
                    from Purchase.models import PurchaseOrder, Bill
                    if PurchaseOrder.objects.using(getattr(company, "db_name", "default")).filter(document_currency=cur).exists():
                        usage_msgs.append('purchase orders')
                except Exception:
                    pass
                try:
                    if _exchange_rate_qs(company) is not None and _exchange_rate_qs(company).filter(currency_id=cur.pk).exists():
                        usage_msgs.append('exchange rates')
                except Exception:
                    pass

                if usage_msgs:
                    messages.error(
                        request,
                        "Cannot unset base currency while it's used by: " + ", ".join(usage_msgs) + ". Assign a new base currency or remove usages first.",
                    )
                    return redirect_with_company(request, "currencies:currency_list")

                # Safe to unset: clear company base_currency
                cur.is_base = False
                try:
                    _sync_company_base_currency(company, '')
                except Exception:
                    pass
            default_symbol, default_name = _currency_display_defaults(cur.code)
            cur.symbol = symbol or default_symbol
            cur.name = name or default_name
            cur.decimal_places = decimals
            cur.display_format = display_format
            if is_base:
                cur.is_base = True
            cur.save()
            if is_base:
                currency_qs.filter(company_id=company.pk, is_base=True).exclude(pk=cur.pk).update(is_base=False)
                if not cur.is_base:
                    cur.is_base = True
                    cur.save(update_fields=["is_base"])
        messages.success(request, "Currency updated.")
        return redirect_with_company(request, "currencies:currency_list")

    return render(
        request,
        "currencies/currency_form.html",
        {"title": "Edit currency", "currency_obj": cur, "company": company, "format_choices": Currency.FORMAT_CHOICES},
    )


@login_required
@require_POST
def toggle_exchange_feeds(request):
    company = _company_for_request(request)
    if not company:
        messages.error(request, "No organisation found.")
        return redirect_with_company(request, "website:index")
    # Toggle boolean safely even if attribute missing
    current = bool(getattr(company, "exchange_rate_feeds_enabled", False))
    company.exchange_rate_feeds_enabled = not current
    try:
        company.save(update_fields=["exchange_rate_feeds_enabled"])
    except Exception:
        # Best-effort: fallback to full save
        company.save()
    state = "enabled" if company.exchange_rate_feeds_enabled else "disabled"
    messages.success(request, f"Exchange rate feeds {state}.")
    return redirect_with_company(request, "currencies:currency_list")


@login_required
@require_POST
def currency_delete(request, pk):
    company = _company_for_request(request)
    currency_qs = _currency_qs(company)
    if currency_qs is None:
        messages.error(request, "Company database is not configured.")
        return redirect_with_company(request, "currencies:currency_list")
    cur = get_object_or_404(currency_qs.filter(company_id=company.pk), pk=pk)

    # Prevent deletion if this is the base currency
    if cur.is_base:
        messages.error(request, "Cannot delete the base currency.")
        return redirect_with_company(request, "currencies:currency_list")

    # Check for usage in common transactional models and exchange rates
    usages = []
    try:
        from sales.models import SalesInvoice
        if SalesInvoice.objects.filter(document_currency=cur).exists():
            usages.append('sales invoices')
    except Exception:
        pass
    try:
        from Purchase.models import PurchaseOrder, Bill
        if hasattr(PurchaseOrder, 'document_currency') and PurchaseOrder.objects.filter(document_currency=cur).exists():
            usages.append('purchase orders')
        if hasattr(Bill, 'document_currency') and Bill.objects.filter(document_currency=cur).exists():
            usages.append('purchase bills')
    except Exception:
        pass
    try:
        rate_qs = _exchange_rate_qs(company)
        if rate_qs is not None and rate_qs.filter(currency_id=cur.pk).exists():
            usages.append('exchange rates')
    except Exception:
        pass

    if usages:
        messages.error(request, "Cannot delete currency because it's used by: " + ", ".join(sorted(set(usages))) + ".")
        return redirect_with_company(request, "currencies:currency_list")

    try:
        cur.delete()
        messages.success(request, "Currency removed.")
    except ProtectedError:
        messages.error(request, "This currency is in use and cannot be deleted.")
    return redirect_with_company(request, "currencies:currency_list")


@login_required
def exchange_rate_list(request, pk):
    company = _company_for_request(request)
    currency_qs = _currency_qs(company)
    rate_qs = _exchange_rate_qs(company)
    if currency_qs is None or rate_qs is None:
        messages.error(request, "Company database is not configured.")
        return redirect_with_company(request, "currencies:currency_list")
    cur = get_object_or_404(currency_qs.filter(company_id=company.pk), pk=pk)
    rates = rate_qs.filter(currency_id=cur.pk).order_by("-effective_from", "-id")
    return render(
        request,
        "currencies/exchange_rate_list.html",
        {"currency_obj": cur, "rates": rates, "company": company},
    )


@login_required
def exchange_rate_add(request, pk):
    company = _company_for_request(request)
    currency_qs = _currency_qs(company)
    rate_qs = _exchange_rate_qs(company)
    if currency_qs is None or rate_qs is None:
        messages.error(request, "Company database is not configured.")
        return redirect_with_company(request, "currencies:currency_list")
    cur = get_object_or_404(currency_qs.filter(company_id=company.pk), pk=pk)
    if cur.is_base:
        messages.info(request, "No exchange rate is stored for the base currency.")
        return redirect_with_company(request, "currencies:exchange_rate_list", pk=cur.pk)

    if request.method == "POST":
        eff = request.POST.get("effective_from")
        raw_rate = (request.POST.get("rate") or "").strip()
        try:
            rate = Decimal(raw_rate)
        except (InvalidOperation, TypeError):
            messages.error(request, "Enter a valid rate.")
            return redirect_with_company(request, "currencies:exchange_rate_list", pk=cur.pk)
        if rate <= 0:
            messages.error(request, "Rate must be positive.")
            return redirect_with_company(request, "currencies:exchange_rate_list", pk=cur.pk)
        rate_qs.update_or_create(
            currency_id=cur.pk,
            effective_from=eff,
            defaults={"rate": rate, "source": ExchangeRate.SOURCE_MANUAL},
        )
        messages.success(request, "Exchange rate saved.")
        return redirect_with_company(request, "currencies:exchange_rate_list", pk=cur.pk)

    return redirect_with_company(request, "currencies:exchange_rate_list", pk=cur.pk)


@login_required
@require_POST
def exchange_rate_delete(request, rate_id):
    company = _company_for_request(request)
    rate_qs = _exchange_rate_qs(company)
    if rate_qs is None:
        messages.error(request, "Company database is not configured.")
        return redirect_with_company(request, "currencies:currency_list")
    rate = get_object_or_404(rate_qs, pk=rate_id)
    if rate.currency.company_id != company.id:
        messages.error(request, "Invalid rate.")
        return redirect_with_company(request, "currencies:currency_list")
    pk = rate.currency_id
    if rate.source != ExchangeRate.SOURCE_MANUAL:
        messages.error(request, "Only manually entered rates can be deleted here.")
        return redirect_with_company(request, "currencies:exchange_rate_list", pk=pk)
    rate.delete()
    messages.success(request, "Exchange rate deleted.")
    return redirect_with_company(request, "currencies:exchange_rate_list", pk=pk)


@login_required
def api_get_vendor_currency(request):
    """API: given a vendor id, return the vendor's preferred currency and effective rate to base.

    GET params:
      - vendor_id: vendor PK
      - date: YYYY-MM-DD (optional)
    """
    company = _company_for_request(request)
    vendor_id = request.GET.get("vendor_id")
    currency_id = request.GET.get("currency_id")
    date_str = request.GET.get("date")
    try:
        from Purchase.models import Vendor
        from .services import get_effective_rate_to_base
        from datetime import datetime

        currency_qs = _currency_qs(company)
        rate_qs = _exchange_rate_qs(company)
        cur = None
        if currency_qs is not None and currency_id and currency_id.isdigit():
            cur = currency_qs.filter(company_id=company.pk, pk=int(currency_id)).first()
            
        vendor = None
        if not cur and vendor_id and vendor_id.isdigit():
            vendor = Vendor.objects.filter(pk=int(vendor_id)).first()

        # resolve currency: prefer vendor.preferred_currency then vendor.currency then company base
        if not cur and vendor:
            cur = getattr(vendor, 'preferred_currency', None)
            if not cur and getattr(vendor, 'currency', None):
                if currency_qs is not None:
                    cur = currency_qs.filter(company_id=company.pk, code=(vendor.currency or '').strip().upper()[:3]).first()

        # fallback to base
        if not cur:
            if currency_qs is not None:
                cur = currency_qs.filter(company_id=company.pk, is_base=True).first()

        if date_str:
            try:
                as_of = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                as_of = timezone.now().date()
        else:
            as_of = timezone.now().date()

        # Try to find the exact ExchangeRate row used so we can return source and effective_from
        rate = get_effective_rate_to_base(cur, as_of) if cur else Decimal('1')
        rate_source = None
        rate_effective = None
        if cur:
            row = (
                rate_qs.filter(currency_id=cur.pk, effective_from__lte=as_of)
                .order_by("-effective_from", "-id")
                .first()
            )
            if row:
                rate = row.rate or rate
                rate_source = row.source
                rate_effective = row.effective_from

        # Format rate for UI/API consumer: 6 decimal places
        try:
            formatted_rate = str((rate.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)))
        except Exception:
            formatted_rate = str(rate)
        return JsonResponse({
            "ok": True,
            "currency_id": cur.pk if cur else None,
            "currency_code": cur.code if cur else None,
            "currency_symbol": getattr(cur, 'symbol', None) if cur else None,
            "rate": formatted_rate,
            "date": as_of.isoformat(),
            "rate_source": rate_source,
            "rate_effective_from": rate_effective.isoformat() if rate_effective else None,
        })
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})


@login_required
def api_get_customer_currency(request):
    """API: given a customer id, return the customer's preferred currency and effective rate to base.

    GET params:
      - customer_id: customer PK
      - date: YYYY-MM-DD (optional)
    """
    company = _company_for_request(request)
    customer_id = request.GET.get("customer_id")
    currency_id = request.GET.get("currency_id")
    date_str = request.GET.get("date")
    try:
        from customer.models import Customer
        from .services import get_effective_rate_to_base
        from datetime import datetime

        currency_qs = _currency_qs(company)
        rate_qs = _exchange_rate_qs(company)
        cur = None
        if currency_qs is not None and currency_id and currency_id.isdigit():
            cur = currency_qs.filter(company_id=company.pk, pk=int(currency_id)).first()
        
        customer = None
        if not cur and customer_id and customer_id.isdigit():
            customer = Customer.objects.filter(pk=int(customer_id)).first()

        # resolve currency: prefer customer.preferred_currency then customer.currency then company base
        if not cur and customer:
            cur = getattr(customer, 'preferred_currency', None)
            if not cur and getattr(customer, 'currency', None):
                if currency_qs is not None:
                    cur = currency_qs.filter(company_id=company.pk, code=(customer.currency or '').strip().upper()[:3]).first()

        # fallback to base
        if not cur:
            if currency_qs is not None:
                cur = currency_qs.filter(company_id=company.pk, is_base=True).first()
        if date_str:
            try:
                as_of = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                as_of = timezone.now().date()
        else:
            as_of = timezone.now().date()

        rate = get_effective_rate_to_base(cur, as_of) if cur else Decimal('1')
        rate_source = None
        rate_effective = None
        if cur:
            row = (
                rate_qs.filter(currency_id=cur.pk, effective_from__lte=as_of)
                .order_by("-effective_from", "-id")
                .first()
            )
            if row:
                rate = row.rate or rate
                rate_source = row.source
                rate_effective = row.effective_from

        # Format rate for UI/API consumer: 6 decimal places
        try:
            formatted_rate = str((rate.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)))
        except Exception:
            formatted_rate = str(rate)
        return JsonResponse({
            "ok": True,
            "currency_id": cur.pk if cur else None,
            "currency_code": cur.code if cur else None,
            "currency_symbol": getattr(cur, 'symbol', None) if cur else None,
            "rate": formatted_rate,
            "date": as_of.isoformat(),
            "rate_source": rate_source,
            "rate_effective_from": rate_effective.isoformat() if rate_effective else None,
        })
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})
