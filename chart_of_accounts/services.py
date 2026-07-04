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
    # VAT / sales tax / turnover tax
    "1020707", "2020213",
    "1020708", "2020214",
    "40207", "40224", "2020215",
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


def _infer_legacy_tax_type_from_country(country_code):
    country_code = str(country_code or "").strip().upper()
    if country_code == "IN":
        return "GST"
    if country_code:
        return "VAT"
    return ""


def get_company_tax_type(using="default"):
    if using != "default" and not _db_has_chart_of_accounts_table(using):
        using = "default"
    company = Company.objects.using(using).order_by("id").first()
    if not company:
        return ""

    tax_type = str(getattr(company, "tax_type", "") or "").strip().upper()
    if tax_type:
        return tax_type

    # Legacy company rows may have a blank tax_type. Keep old data working,
    # but new behavior should come from Company.tax_type.
    return _infer_legacy_tax_type_from_country(getattr(company, "country", ""))


def _account_spec(code, name, account_type, parent_code, description):
    return {
        "code": code,
        "name": name,
        "type": account_type,
        "parent": parent_code,
        "description": description,
        "is_header": False,
    }


TAX_ACCOUNT_TEMPLATES = {
    "GST": [
        _account_spec("40207", "GST Expense", "4", "402", "GST expense"),
        _account_spec("1020701", "Input Tax CGST", "1", "10207", "Input CGST recoverable"),
        _account_spec("1020702", "Input Tax IGST", "1", "10207", "Input IGST recoverable"),
        _account_spec("1020703", "Input Tax SGST", "1", "10207", "Input SGST recoverable"),
        _account_spec("1020704", "Output Tax CGST Refund", "1", "10207", "CGST refund receivable"),
        _account_spec("1020705", "Output Tax IGST Refund", "1", "10207", "IGST refund receivable"),
        _account_spec("1020706", "Output Tax SGST Refund", "1", "10207", "SGST refund receivable"),
        _account_spec("2020202", "Input Tax CGST RCM", "2", "20202", "Input CGST reverse charge payable"),
        _account_spec("2020203", "Input Tax IGST RCM", "2", "20202", "Input IGST reverse charge payable"),
        _account_spec("2020204", "Input Tax SGST RCM", "2", "20202", "Input SGST reverse charge payable"),
        _account_spec("2020205", "Output Tax CGST", "2", "20202", "Output CGST payable"),
        _account_spec("2020206", "Output Tax CGST RCM", "2", "20202", "Output CGST reverse charge payable"),
        _account_spec("2020207", "Output Tax IGST", "2", "20202", "Output IGST payable"),
        _account_spec("2020208", "Output Tax IGST RCM", "2", "20202", "Output IGST reverse charge payable"),
        _account_spec("2020209", "Output Tax SGST", "2", "20202", "Output SGST payable"),
        _account_spec("2020210", "Output Tax SGST RCM", "2", "20202", "Output SGST reverse charge payable"),
    ],
    "VAT": [
        _account_spec("1020707", "Input VAT", "1", "10207", "Recoverable VAT on purchases"),
        _account_spec("2020213", "Output VAT", "2", "20202", "VAT collected on sales payable to authorities"),
    ],
    "SALES": [
        _account_spec("1020708", "Input Sales Tax", "1", "10207", "Recoverable sales tax on purchases"),
        _account_spec("2020214", "Sales Tax Payable", "2", "20202", "Sales tax collected on sales payable to authorities"),
    ],
    "TURNOVER": [
        _account_spec("40224", "Turnover Tax Expense", "4", "402", "Turnover tax expense"),
        _account_spec("2020215", "Turnover Tax Payable", "2", "20202", "Turnover tax payable to authorities"),
    ],
}


TDS_TCS_ACCOUNT_TEMPLATES = [
    _account_spec("1020711", "TDS Receivable", "1", "10207", "TDS withheld by customer and recoverable as tax credit"),
    _account_spec("1020712", "TCS Receivable", "1", "10207", "TCS collected by supplier and recoverable as tax credit"),
    _account_spec("2020212", "TDS Payable", "2", "20202", "TDS withheld from supplier and payable to authorities"),
    _account_spec("2020216", "TCS Payable", "2", "20202", "TCS collected from customer and payable to authorities"),
]


def _tax_accounts_for_type(tax_type):
    tax_type = str(tax_type or "").strip().upper()
    return TAX_ACCOUNT_TEMPLATES.get(tax_type, [])


def ensure_tax_accounts_for_type(tax_type=None, using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return []

    tax_type = str(tax_type or get_company_tax_type(using=using) or "").strip().upper()
    accounts = _tax_accounts_for_type(tax_type)
    for account in accounts:
        _upsert_account(account, using=using)
    return accounts


@transaction.atomic
def sync_chart_of_accounts_for_country(country_code, using="default", tax_type=None):
    if not _db_has_chart_of_accounts_table(using):
        return

    selected_tax_accounts = (
        _tax_accounts_for_type(tax_type)
        or get_tax_template_for_country(country_code)
        or _tax_accounts_for_type(_infer_legacy_tax_type_from_country(country_code))
    )
    selected_tax_codes = {account["code"] for account in selected_tax_accounts}

    for account in GLOBAL_ACCOUNTS:
        _upsert_account(account, using=using)

    for account in selected_tax_accounts:
        _upsert_account(account, using=using)

    ensure_tds_tcs_accounts(using=using)

    # Only deactivate known tax accounts when we have a selected tax template.
    # An empty template should never wipe all seeded tax accounts.
    if selected_tax_codes:
        obsolete_codes = ALL_TAX_CODES - selected_tax_codes
        ChartOfAccounts.objects.using(using).filter(code__in=obsolete_codes).update(
            active=False,
            status=False,
        )


def sync_chart_of_accounts_from_company(company):
    country_code = str(getattr(company, "country", "") or "")
    tax_type = str(getattr(company, "tax_type", "") or "").strip().upper()
    if _db_has_chart_of_accounts_table("default"):
        sync_chart_of_accounts_for_country(country_code, using="default", tax_type=tax_type)

    if company.db_name and company.db_created:
        register_database(company.db_name)
        if _db_has_chart_of_accounts_table(company.db_name):
            sync_chart_of_accounts_for_country(country_code, using=company.db_name, tax_type=tax_type)


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
    return ensure_tax_accounts_for_type("VAT", using=using)


def ensure_tds_tcs_accounts(using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return []
    for account in TDS_TCS_ACCOUNT_TEMPLATES:
        _upsert_account(account, using=using)
    return TDS_TCS_ACCOUNT_TEMPLATES


def resolve_tds_tcs_account(tds_tcs_type, direction="receivable", using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return None

    ensure_tds_tcs_accounts(using=using)

    tds_tcs_type = str(tds_tcs_type or "").strip().lower()
    direction = str(direction or "").strip().lower()

    if tds_tcs_type == "tds":
        if direction == "receivable":
            names = ["TDS Receivable"]
        else:
            names = ["TDS Payable"]
    elif tds_tcs_type == "tcs":
        if direction == "receivable":
            names = ["TCS Receivable"]
        else:
            names = ["TCS Payable"]
    else:
        return None

    return _find_first_account(names, using=using)


def resolve_tax_account(tax_code, direction="input", using="default"):
    if not _db_has_chart_of_accounts_table(using):
        return None

    tax_code = normalize_tax_code(tax_code)
    company_tax_type = get_company_tax_type(using=using)
    ensure_tax_accounts_for_type(company_tax_type, using=using)

    if direction == "input":
        if company_tax_type == "GST":
            name_map = {
                "CGST": ["Input Tax CGST"],
                "SGST": ["Input Tax SGST"],
                "IGST": ["Input Tax IGST"],
            }
            acct = _find_first_account(name_map.get(tax_code, []), using=using)
            if acct:
                return acct
            # India fallback
            fallback_names = [
                "Input Tax",
                "Tax Receivable",
                "Tax Asset",
            ]
        elif company_tax_type == "VAT":
            fallback_names = [
                "Input VAT",
                "VAT Receivable",
            ]
        elif company_tax_type == "SALES":
            fallback_names = [
                "Input Sales Tax",
                "Sales Tax Receivable",
            ]
        elif company_tax_type == "TURNOVER":
            fallback_names = [
                "Turnover Tax Expense",
            ]
        else:
            return None

        return _find_first_account(fallback_names, using=using)

    # Output direction
    if company_tax_type == "GST":
        name_map = {
            "CGST": ["Output Tax CGST"],
            "SGST": ["Output Tax SGST"],
            "IGST": ["Output Tax IGST"],
        }
        acct = _find_first_account(name_map.get(tax_code, []), using=using)
        if acct:
            return acct
        # India fallback
        fallback_names = [
            "Output Tax",
            "Tax Payable",
            "Duties and Taxes",
        ]
    elif company_tax_type == "VAT":
        fallback_names = [
            "Output VAT",
            "VAT Payable",
        ]
    elif company_tax_type == "SALES":
        fallback_names = [
            "Sales Tax Payable",
            "Output Sales Tax",
        ]
    elif company_tax_type == "TURNOVER":
        fallback_names = [
            "Turnover Tax Payable",
        ]
    else:
        return None
    
    return _find_first_account(fallback_names, using=using)
