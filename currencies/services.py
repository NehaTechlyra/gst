"""
Multi-currency helpers: resolve party currency, effective rates, document FX fields.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from django.db.models import Q

from django.conf import settings
import logging

# Try importing requests for remote country->currency lookup. If unavailable,
# we'll gracefully fall back to a small local mapping.
try:
    import requests  # type: ignore
except Exception:
    requests = None

# Small local fallback map used when network or `requests` is unavailable.
COUNTRY_TO_CURRENCY = {
    "IN": "INR",
    "US": "USD",
    "GB": "GBP",
    "AE": "AED",
    "SA": "SAR",
    "CA": "CAD",
    "AU": "AUD",
    "NZ": "NZD",
    "JP": "JPY",
    "CN": "CNY",
    "SG": "SGD",
    "EU": "EUR",
}


from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def infer_currency_code_from_country(country_value) -> str:
    """Infer a 3-letter currency code from a country value.

    Strategy:
    - Accepts a CountryField-like object, an ISO alpha-2 code, or a country name.
    - If possible, query the public RestCountries API for authoritative mapping.
    - If network or `requests` is unavailable, fall back to `COUNTRY_TO_CURRENCY`.
    - Return empty string when no mapping is available.
    """
    if not country_value:
        return ""

    try:
        code_or_name = getattr(country_value, "code", None) or str(country_value)
    except Exception:
        code_or_name = str(country_value)

    code_or_name = (code_or_name or "").strip()
    if not code_or_name:
        return ""

    # If we have a 2-letter code, prefer an API lookup
    candidate = code_or_name.upper()
    if len(candidate) == 2:
        # Prefer API when enabled
        if getattr(settings, 'USE_COUNTRY_API', True) and requests:
            try:
                resp = requests.get(f"https://restcountries.com/v3.1/alpha/{candidate}", timeout=3)
                if resp.ok:
                    data = resp.json()
                    if isinstance(data, list):
                        data = data[0]
                    currencies = data.get("currencies") or {}
                    if isinstance(currencies, dict) and currencies:
                        return next(iter(currencies.keys()))
            except Exception as e:
                logger.exception("Country API alpha lookup failed for %s", candidate)

        # Fallback to small local map
        return COUNTRY_TO_CURRENCY.get(candidate, "")

    # If candidate is a name, try name-based lookup via API first
    name_candidate = candidate
    if getattr(settings, 'USE_COUNTRY_API', True) and requests:
        try:
            resp = requests.get(f"https://restcountries.com/v3.1/name/{name_candidate}", timeout=3)
            if resp.ok:
                data = resp.json()
                if isinstance(data, list) and data:
                    currencies = data[0].get("currencies") or {}
                    if isinstance(currencies, dict) and currencies:
                        return next(iter(currencies.keys()))
        except Exception as e:
            logger.exception("Country API name lookup failed for %s", name_candidate)

    # Heuristic name checks and local map fallback
    lower = candidate.lower()
    if "india" in lower:
        return "INR"
    if "united states" in lower or "usa" in lower or "us" == lower:
        return "USD"
    if "united kingdom" in lower or "uk" in lower:
        return "GBP"

    # Last attempt: check if the value looks like an alpha-3 currency code already
    if len(candidate) == 3 and candidate.isalpha():
        return candidate.upper()

    return ""


def currency_display_defaults(code: str) -> Tuple[str, str]:
    code = (code or "").strip().upper()[:3]
    try:
        from currencies.utils import get_currency_symbol, get_currency_name

        symbol = get_currency_symbol(code) or code
        name = get_currency_name(code) or code
    except Exception:
        symbol = code
        name = code
    return symbol, name


def base_currency_code_from_country(country_value) -> str:
    return (infer_currency_code_from_country(country_value) or "").strip().upper()[:3]


def ensure_base_currency_row(company, db_alias: str, code: Optional[str] = None):
    if not company or not db_alias or db_alias == "default":
        return None

    code = ((code or getattr(company, "base_currency", None) or "").strip().upper()[:3])
    if not code:
        code = base_currency_code_from_country(getattr(company, "country", None))
    if not code:
        return None

    from currencies.models import Currency
    # Ensure the Company row exists in the target DB before creating/updating
    # currencies that FK to company_company. This prevents IntegrityError when a
    # tenant DB is missing the company row (common in partially-synced setups).
    try:
        from company.models import Company

        if not Company.objects.using(db_alias).filter(pk=company.pk).exists():
            Company.objects.using(db_alias).update_or_create(
                id=company.pk,
                defaults={
                    "name": getattr(company, "name", "") or "Company",
                    "tax_type": (getattr(company, "tax_type", "") or "NONE").strip().upper() or "NONE",
                    "status": True,
                },
            )
    except Exception:
        # Best-effort: if we can't ensure the company row, let the caller handle.
        pass

    symbol, name = currency_display_defaults(code)
    currency_qs = Currency.objects.using(db_alias)
    currency_qs.filter(company_id=company.pk, is_base=True).exclude(code=code).update(is_base=False)
    currency, _ = currency_qs.update_or_create(
        company_id=company.pk,
        code=code,
        defaults={
            "symbol": symbol,
            "name": name,
            "decimal_places": 2,
            "is_base": True,
            "is_active": True,
        },
    )
    return currency


def _quantize_money(value: Decimal, places: int = 2) -> Decimal:
    q = Decimal("1").scaleb(-places)  # 10^-places
    return value.quantize(q, rounding=ROUND_HALF_UP)


def get_base_currency(company):
    from currencies.models import Currency

    base = (
        Currency.objects.filter(company=company, is_base=True, is_active=True)
        .order_by("id")
        .first()
    )
    if base:
        return base

    # Prefer explicit company.base_currency when present
    explicit_code = (getattr(company, "base_currency", None) or "").strip().upper()[:3]

    # If not explicit, try to infer from company.country
    if not explicit_code:
        inferred = infer_currency_code_from_country(getattr(company, "country", None))
        explicit_code = (inferred or "").strip().upper()[:3]

    # If company already has any currencies defined, use the first available
    if not explicit_code:
        existing = Currency.objects.filter(company=company, is_active=True).order_by('-is_base', 'code').first()
        if existing:
            # Ensure a single base currency
            Currency.objects.filter(company=company, is_base=True).exclude(pk=existing.pk).update(is_base=False)
            if not existing.is_base:
                existing.is_base = True
                existing.save(update_fields=["is_base"])
            return existing

    # Last resort: fallback to explicit_code or INR to avoid returning None to callers
    code = explicit_code or "INR"
    try:
        from currencies.utils import get_currency_symbol, get_currency_name
        sym = get_currency_symbol(code) or code
        nm = get_currency_name(code) or code
    except Exception:
        sym = code
        nm = code

    base, _ = Currency.objects.get_or_create(
        company=company,
        code=code,
        defaults={
            "symbol": sym,
            "name": nm,
            "decimal_places": 2,
            "is_base": True,
            "is_active": True,
        },
    )
    Currency.objects.filter(company=company, is_base=True).exclude(pk=base.pk).update(is_base=False)
    if not base.is_base:
        base.is_base = True
        base.save(update_fields=["is_base"])
    return base


def resolve_currency_for_customer(customer, company):
    from currencies.models import Currency

    base = get_base_currency(company)
    if not customer:
        return base
    if getattr(customer, "preferred_currency_id", None):
        c = Currency.objects.filter(
            pk=customer.preferred_currency_id, company=company, is_active=True
        ).first()
        if c:
            return c
    code = (getattr(customer, "currency", None) or base.code or "").strip().upper()[:3]
    if not code:
        return base
    c = Currency.objects.filter(company=company, code=code, is_active=True).first()
    if c:
        return c
    return base


def resolve_currency_for_vendor(vendor, company):
    from currencies.models import Currency

    base = get_base_currency(company)
    if not vendor:
        return base
    if getattr(vendor, "preferred_currency_id", None):
        c = Currency.objects.filter(
            pk=vendor.preferred_currency_id, company=company, is_active=True
        ).first()
        if c:
            return c
    code = (getattr(vendor, "currency", None) or base.code or "").strip().upper()[:3]
    if not code:
        return base
    c = Currency.objects.filter(company=company, code=code, is_active=True).first()
    if c:
        return c
    return base


def get_effective_rate_to_base(currency, as_of_date) -> Decimal:
    """
    Return multiplier: multiply an amount in `currency` by this to get base currency.
    Base currency always returns 1.
    """
    from currencies.models import Currency, ExchangeRate

    if not currency or getattr(currency, "is_base", False):
        return Decimal("1")

    if as_of_date is None:
        from django.utils import timezone

        as_of_date = timezone.now().date()

    row = (
        ExchangeRate.objects.filter(currency=currency, effective_from__lte=as_of_date)
        .order_by("-effective_from", "-id")
        .first()
    )
    if row and row.rate and row.rate > 0:
        return row.rate
    return Decimal("1")


def parse_currency_fx_from_post(post_data, company):
    """
    Read document_currency, fx_rate_to_base, fx_rate_date from POST/request.POST.
    Returns (document_currency|None, fx_rate_override|None, fx_rate_date|None).
    """
    from currencies.models import Currency
    from datetime import datetime

    doc_cur = None
    raw_id = (post_data.get("document_currency") or "").strip()
    if raw_id.isdigit():
        doc_cur = Currency.objects.filter(
            pk=int(raw_id), company=company, is_active=True
        ).first()

    rate_override = None
    rs = (post_data.get("fx_rate_to_base") or "").strip()
    if rs:
        try:
            r = Decimal(rs)
            if r >= 0:
                rate_override = r
        except Exception:
            pass

    fx_date = None
    ds = (post_data.get("fx_rate_date") or "").strip()
    if ds:
        try:
            fx_date = datetime.strptime(ds, "%Y-%m-%d").date()
        except Exception:
            pass

    return doc_cur, rate_override, fx_date


def apply_sales_invoice_fx(
    invoice,
    company,
    *,
    document_currency=None,
    fx_rate_to_base_override=None,
    fx_rate_date_override=None,
) -> None:
    """Populate document_currency, fx_rate_to_base, fx_rate_date, total_amount_base."""
    from sales.models import SalesInvoice

    if not isinstance(invoice, SalesInvoice) or not invoice.pk:
        return
    customer = invoice.customer
    doc_cur = document_currency or resolve_currency_for_customer(customer, company)
    as_of = fx_rate_date_override if fx_rate_date_override is not None else invoice.date
    if fx_rate_to_base_override is not None:
        rate = fx_rate_to_base_override
    else:
        rate = get_effective_rate_to_base(doc_cur, as_of)
    total_doc = Decimal(str(invoice.total_amount or 0))
    total_base = _quantize_money(total_doc * rate, places=2)
    SalesInvoice.objects.filter(pk=invoice.pk).update(
        document_currency=doc_cur,
        fx_rate_to_base=rate,
        fx_rate_date=as_of,
        total_amount_base=total_base,
    )
    invoice.document_currency = doc_cur
    invoice.fx_rate_to_base = rate
    invoice.fx_rate_date = as_of
    invoice.total_amount_base = total_base


def apply_performa_invoice_fx(
    invoice,
    company,
    *,
    document_currency=None,
    fx_rate_to_base_override=None,
    fx_rate_date_override=None,
) -> None:
    """Populate document_currency, fx_rate_to_base, fx_rate_date, total_amount_base."""
    from sales.models import PerformaInvoice

    if not isinstance(invoice, PerformaInvoice) or not invoice.pk:
        return
    customer = invoice.customer
    doc_cur = document_currency or resolve_currency_for_customer(customer, company)
    as_of = fx_rate_date_override if fx_rate_date_override is not None else invoice.date
    if fx_rate_to_base_override is not None:
        rate = fx_rate_to_base_override
    else:
        rate = get_effective_rate_to_base(doc_cur, as_of)
    total_doc = Decimal(str(invoice.total_amount or 0))
    total_base = _quantize_money(total_doc * rate, places=2)
    PerformaInvoice.objects.filter(pk=invoice.pk).update(
        document_currency=doc_cur,
        fx_rate_to_base=rate,
        fx_rate_date=as_of,
        total_amount_base=total_base,
    )
    invoice.document_currency = doc_cur
    invoice.fx_rate_to_base = rate
    invoice.fx_rate_date = as_of
    invoice.total_amount_base = total_base


def apply_bill_fx(
    bill,
    company,
    *,
    document_currency=None,
    fx_rate_to_base_override=None,
    fx_rate_date_override=None,
) -> None:
    from Purchase.models import Bill

    if not isinstance(bill, Bill) or not bill.pk:
        return
    vendor = bill.vendor
    doc_cur = document_currency or resolve_currency_for_vendor(vendor, company)
    as_of = fx_rate_date_override if fx_rate_date_override is not None else bill.date
    if fx_rate_to_base_override is not None:
        rate = fx_rate_to_base_override
    else:
        rate = get_effective_rate_to_base(doc_cur, as_of)
    total_doc = Decimal(str(bill.total_amount or 0))
    total_base = _quantize_money(total_doc * rate, places=2)
    Bill.objects.filter(pk=bill.pk).update(
        document_currency=doc_cur,
        fx_rate_to_base=rate,
        fx_rate_date=as_of,
        total_amount_base=total_base,
    )
    bill.document_currency = doc_cur
    bill.fx_rate_to_base = rate
    bill.fx_rate_date = as_of
    bill.total_amount_base = total_base


def apply_purchase_order_fx(
    order,
    company,
    *,
    document_currency=None,
    fx_rate_to_base_override=None,
    fx_rate_date_override=None,
) -> None:
    from Purchase.models import PurchaseOrder

    if not isinstance(order, PurchaseOrder) or not order.pk:
        return
    vendor = order.vendor
    doc_cur = document_currency or resolve_currency_for_vendor(vendor, company)
    as_of = fx_rate_date_override if fx_rate_date_override is not None else order.date
    if fx_rate_to_base_override is not None:
        rate = fx_rate_to_base_override
    else:
        rate = get_effective_rate_to_base(doc_cur, as_of)
    total_doc = Decimal(str(order.total_amount or 0))
    total_base = _quantize_money(total_doc * rate, places=2)
    PurchaseOrder.objects.filter(pk=order.pk).update(
        document_currency=doc_cur,
        fx_rate_to_base=rate,
        fx_rate_date=as_of,
        total_amount_base=total_base,
    )
    order.document_currency = doc_cur
    order.fx_rate_to_base = rate
    order.fx_rate_date = as_of
    order.total_amount_base = total_base


def refresh_document_total_base(obj) -> None:
    """Recompute total_amount_base from total_amount × fx_rate_to_base (after total changes)."""
    rate = getattr(obj, "fx_rate_to_base", None) or Decimal("1")
    if rate < 0:
        rate = Decimal("1")
    total_doc = Decimal(str(getattr(obj, "total_amount", None) or 0))
    total_base = _quantize_money(total_doc * rate, places=2)
    model = obj.__class__
    model.objects.filter(pk=obj.pk).update(total_amount_base=total_base)
    obj.total_amount_base = total_base


def document_to_base_ratio(invoice_or_bill) -> Decimal:
    """Scale factor from document currency totals to base (for journal lines)."""
    doc = Decimal(str(getattr(invoice_or_bill, "total_amount", None) or 0))
    base_amt = getattr(invoice_or_bill, "total_amount_base", None)
    if base_amt is not None and doc and doc != 0:
        return (Decimal(str(base_amt)) / doc).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)
    rate = getattr(invoice_or_bill, "fx_rate_to_base", None) or Decimal("1")
    return rate if rate > 0 else Decimal("1")


def scale_amount_for_journal(amount: Decimal, invoice_or_bill) -> Decimal:
    r = document_to_base_ratio(invoice_or_bill)
    return _quantize_money(Decimal(str(amount or 0)) * r, places=2)
