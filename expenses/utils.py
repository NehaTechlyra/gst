# expenses/utils.py
from chart_of_accounts.services import normalize_tax_code   # or wherever normalize_tax_code actually lives — check its import in views.py

def _get_tax_type_code(tax):
    return normalize_tax_code(getattr(tax, 'taxtype', None))