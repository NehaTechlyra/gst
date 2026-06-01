def company_base_currency_symbol(request):
    """Context processor that exposes the company's base currency symbol to templates.

    Returns a dict with key `company_base_currency_symbol` containing a single-character
    or string symbol (falls back to '₹' if unresolved).
    """
    from company.models import Company
    from .utils import get_currency_symbol as _get_currency_symbol

    symbol = '₹'
    company = None
    if request is not None and getattr(request, 'session', None):
        cid = request.session.get('company_id')
        if cid:
            company = Company.objects.filter(pk=cid).first()
    if company is None:
        company = Company.objects.order_by('id').first()

    try:
        if company and getattr(company, 'base_currency', None):
            code = (company.base_currency or '').strip()
            if code:
                resolved = _get_currency_symbol(code)
                if resolved:
                    symbol = resolved
                else:
                    symbol = code
    except Exception:
        # Keep fallback symbol
        pass

    return { 'company_base_currency_symbol': symbol }
