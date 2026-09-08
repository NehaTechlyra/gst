DEFAULT_DECIMAL_PLACES = 2


def get_decimal_places(currency) -> int:
    """
    Resolve the number of decimal places to use for a given currency.

    Accepts:
      - a Currency model instance (uses .decimal_places)
      - an ISO code string (looked up against the current company's Currency rows)
      - None (returns the default of 2)

    Always falls back to DEFAULT_DECIMAL_PLACES (2) if nothing usable is found,
    so this is always safe to call even with incomplete data.
    """
    if currency is None:
        return DEFAULT_DECIMAL_PLACES

    # Already a Currency instance (or anything with a decimal_places attr)
    places = getattr(currency, 'decimal_places', None)
    if places is not None:
        try:
            return int(places)
        except (TypeError, ValueError):
            return DEFAULT_DECIMAL_PLACES

    # Treat as an ISO code string and look it up
    code = str(currency).strip().upper()[:3]
    if not code:
        return DEFAULT_DECIMAL_PLACES

    try:
        from currencies.models import Currency as CurrencyModel
        row = CurrencyModel.objects.filter(code=code, is_active=True).order_by('id').first()
        if row is not None:
            return int(row.decimal_places)
    except Exception:
        pass

    return DEFAULT_DECIMAL_PLACES


def format_amount(value, currency=None) -> str:
    """
    Format a numeric amount using the decimal places of the given currency
    (Currency instance, ISO code string, or None -> defaults to 2).

    Rounds half-up like Django's floatformat, and always returns a fixed
    number of decimal places (no trimming of trailing zeros), matching the
    existing `floatformat:2` behaviour used throughout the templates.
    """
    from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

    places = get_decimal_places(currency)

    if value is None or value == '':
        value = 0

    try:
        dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    quantizer = Decimal('1') if places == 0 else Decimal('1').scaleb(-places)
    try:
        quantized = dec_value.quantize(quantizer, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return str(value)

    return f"{quantized:.{places}f}"


def currency_queryset_for_request(request):
    from company.models import Company
    from currencies.models import Currency

    company = None
    if request is not None and getattr(request, "session", None):
        cid = request.session.get("company_id")
        if cid:
            company = Company.objects.filter(pk=cid).first()
    if company is None:
        company = Company.objects.order_by("id").first()
    if company is None:
        return Currency.objects.none()
    return Currency.objects.filter(company=company, is_active=True).order_by("code")


def all_currency_choices():
    """Return a list of (code, name) for ISO currencies.

    Uses `pycountry` when installed; falls back to a compact builtin list.
    """
    try:
        import pycountry  # optional dependency

        codes = []
        for c in pycountry.currencies:
            code = getattr(c, 'alpha_3', None) or getattr(c, 'letter', None) or getattr(c, 'alpha_2', None) or None
            if not code:
                # pycountry currency objects expose .alpha_3 for ISO 4217
                code = getattr(c, 'alpha_3', None) or getattr(c, 'alpha_3', None)
            name = getattr(c, 'name', code) or code
            if code:
                codes.append((code.upper(), name))
        # Deduplicate & sort by code
        uniq = sorted({(c[0], c[1]) for c in codes}, key=lambda x: x[0])
        return uniq
    except Exception:
        # Fallback: common currency list
        fallback = [
            ("USD", "US Dollar"), ("EUR", "Euro"), ("GBP", "British Pound"),
            ("INR", "Indian Rupee"), ("AUD", "Australian Dollar"), ("CAD", "Canadian Dollar"),
            ("SGD", "Singapore Dollar"), ("JPY", "Japanese Yen"), ("CNY", "Chinese Yuan"),
            ("NZD", "New Zealand Dollar"), ("AED", "UAE Dirham"), ("SAR", "Saudi Riyal"),
        ]
        return fallback


def get_currency_name(code: str) -> str:
    """Return a human-readable currency name for an ISO code.

    Uses `pycountry` when available; falls back to the code itself.
    """
    if not code:
        return ''
    code = code.strip().upper()[:3]
    try:
        import pycountry
        # Try alpha_3 lookup, then fallback to scanning
        try:
            cur = pycountry.currencies.get(alpha_3=code)
        except Exception:
            cur = None
        if not cur:
            # iterate as a last resort
            for c in pycountry.currencies:
                name = getattr(c, 'name', '')
                cur_code = None
                for attr in ('alpha_3', 'letter', 'alpha_2'):
                    cur_code = getattr(c, attr, None) or cur_code
                if cur_code and cur_code.upper() == code:
                    cur = c
                    break
        if cur:
            return getattr(cur, 'name', code) or code
    except Exception:
        pass
    fallback_names = {
        "USD": "US Dollar",
        "EUR": "Euro",
        "GBP": "British Pound",
        "INR": "Indian Rupee",
        "AUD": "Australian Dollar",
        "CAD": "Canadian Dollar",
        "SGD": "Singapore Dollar",
        "JPY": "Japanese Yen",
        "CNY": "Chinese Yuan",
        "NZD": "New Zealand Dollar",
        "AED": "UAE Dirham",
        "SAR": "Saudi Riyal",
    }
    return fallback_names.get(code, code)


def get_currency_symbol(code: str) -> str:
    """Return a currency symbol for an ISO code.

    Prefers `babel` if available; then falls back to a small hardcoded map;
    otherwise returns the ISO code as a last resort.
    """
    if not code:
        return ''
    code = code.strip().upper()[:3]
    # Try babel
    try:
        from babel.numbers import get_currency_symbol

        try:
            s = get_currency_symbol(code)
            if s:
                return s
        except Exception:
            pass
    except Exception:
        pass

    # Small fallback map for common currencies
    FALLBACK_SYMBOLS = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹', 'AUD': '$', 'CAD': '$',
        'SGD': '$', 'JPY': '¥', 'CNY': '¥', 'NZD': '$', 'AED': 'د.إ', 'SAR': '﷼'
    }
    return FALLBACK_SYMBOLS.get(code, code)
