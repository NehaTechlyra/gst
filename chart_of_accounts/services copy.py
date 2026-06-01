from django.db import transaction, connections

from company.models import Company
from Lyraerp.utils.db_utils import register_database

try:
    from .default_accounts import GLOBAL_ACCOUNTS, get_tax_template_for_country
except ImportError:
    GLOBAL_ACCOUNTS = []

    def get_tax_template_for_country(country_code):
        return []

from .models import ChartOfAccounts


ALL_TAX_CODES = {
    "1020701", "1020702", "1020703", "1020704", "1020705", "1020706",
    "2020201", "2020202", "2020203", "2020204", "2020205", "2020206",
    "2020207", "2020208", "2020209", "2020210", "2020211", "2020212",
    # VAT (non-India)
    "1020707", "2020213",
}


def _db_has_chart_of_accounts_table(using="default"):
    try:
        connection = connections[using]
        table_names = connection.introspection.table_names()
        return ChartOfAccounts._meta.db_table in table_names
    except Exception:
        return False


def _upsert_account(account, using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return None

    parent = None
    parent_code = account.get("parent")
    if parent_code:
        parent = ChartOfAccounts.objects.using(using).filter(code=parent_code).first()

    obj, _ = ChartOfAccounts.objects.using(using).update_or_create(
        code=account["code"],
        defaults={
            "name": account["name"],
            "type": account["type"],
            "parent": parent,
            "description": account.get("description", ""),
            "is_header": account.get("is_header", False),
            "active": True,
            "status": True,
            "search_code": account.get("search_code", ""),
        },
    )
    return obj


@transaction.atomic
def sync_chart_of_accounts_for_country(country_code, using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return

    selected_tax_accounts = get_tax_template_for_country(country_code)
    selected_tax_codes = {account["code"] for account in selected_tax_accounts}

    for account in GLOBAL_ACCOUNTS:
        _upsert_account(account, using=using)

    for account in selected_tax_accounts:
        _upsert_account(account, using=using)

    # Ensure VAT accounts exist for non-India countries, since the seeded COA only includes GST accounts.
    if str(country_code or "").strip().upper() and str(country_code or "").strip().upper() != "IN":
        ensure_vat_accounts(using=using)

    obsolete_codes = ALL_TAX_CODES - selected_tax_codes
    if obsolete_codes:
        ChartOfAccounts.objects.using(using).filter(code__in=obsolete_codes).update(
            active=False,
            status=False,
        )


def sync_chart_of_accounts_from_company(company):
    country_code = str(getattr(company, "country", "") or "")
    if _db_has_chart_of_accounts_table("default"):
        sync_chart_of_accounts_for_country(country_code, using="default")

    if company.db_name and company.db_created:
        register_database(company.db_name)
        if _db_has_chart_of_accounts_table(company.db_name):
            sync_chart_of_accounts_for_country(country_code, using=company.db_name)


def get_company_country_code(using="default"):
    if using != "default" and not _db_has_chart_of_accounts_table(using):
        using = "default"
    company = Company.objects.using(using).order_by("id").first()
    return str(getattr(company, "country", "") or "").strip().upper() if company else ""


def normalize_tax_code(value):
    if not value:
        return ""
    if hasattr(value, "taxtype"):
        value = value.taxtype
    if hasattr(value, "name"):
        value = value.name
    return str(value or "").strip().upper()


def _find_first_account(names, using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return None
    for name in names:
        acct = ChartOfAccounts.objects.using(using).filter(name__iexact=name, active=True, status=True).first()
        if acct:
            return acct
    for name in names:
        acct = ChartOfAccounts.objects.using(using).filter(name__icontains=name, active=True, status=True).first()
        if acct:
            return acct
    return None


def ensure_vat_accounts(using="default"):
    """
    Ensure minimal VAT accounts exist for non-India companies.
    Creates:
    - Input VAT under Tax Assets (code 10207) as asset
    - Output VAT under Duties and Taxes (code 20202) as liability
    """
    if not _db_has_chart_of_accounts_table(using):
        return

    # Already present?
    if ChartOfAccounts.objects.using(using).filter(name__iexact="Input VAT", active=True, status=True).exists() and \
       ChartOfAccounts.objects.using(using).filter(name__iexact="Output VAT", active=True, status=True).exists():
        return

    tax_assets_parent = ChartOfAccounts.objects.using(using).filter(code="10207").first()
    duties_taxes_parent = ChartOfAccounts.objects.using(using).filter(code="20202").first()

    # Create if missing (avoid code collisions)
    ChartOfAccounts.objects.using(using).update_or_create(
        code="1020707",
        defaults={
            "name": "Input VAT",
            "type": "1",  # Asset (matches seeded COA which stores numeric types as strings)
            "parent": tax_assets_parent,
            "description": "Recoverable VAT on purchases",
            "is_header": False,
            "active": True,
            "status": True,
            "search_code": "",
        },
    )

    ChartOfAccounts.objects.using(using).update_or_create(
        code="2020213",
        defaults={
            "name": "Output VAT",
            "type": "2",  # Liability
            "parent": duties_taxes_parent,
            "description": "VAT collected on sales payable to authorities",
            "is_header": False,
            "active": True,
            "status": True,
            "search_code": "",
        },
    )


def resolve_tax_account(tax_code, direction="input", using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return None

    tax_code = normalize_tax_code(tax_code)
    country_code = get_company_country_code(using=using)

    if direction == "input":
        if country_code == "IN":
            name_map = {
                "CGST": ["Input Tax CGST"],
                "SGST": ["Input Tax SGST"],
                "IGST": ["Input Tax IGST"],
            }
            acct = _find_first_account(name_map.get(tax_code, []), using=using)
            if acct:
                return acct
        else:
            # For non-India, ensure VAT accounts exist so posting doesn't drop tax lines.
            ensure_vat_accounts(using=using)

        fallback_names = [
            "Input VAT",
            "Input GST",
            "VAT Receivable",
            "GST Receivable",
            "Input Tax",
            "Tax Receivable",
            "Tax Asset",
            "Tax Expense",
        ]
        return _find_first_account(fallback_names, using=using)

    if country_code == "IN":
        name_map = {
            "CGST": ["Output Tax CGST"],
            "SGST": ["Output Tax SGST"],
            "IGST": ["Output Tax IGST"],
        }
        acct = _find_first_account(name_map.get(tax_code, []), using=using)
        if acct:
            return acct
    else:
        ensure_vat_accounts(using=using)

    fallback_names = [
        "Output VAT",
        "Output GST",
        "Sales Tax Payable",
        "VAT Payable",
        "GST Payable",
        "Local Tax Payable",
        "Tax Payable",
        "Duties and Taxes",
    ]
    return _find_first_account(fallback_names, using=using)
