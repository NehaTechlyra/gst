from django.db import DatabaseError

from chart_of_accounts.models import ChartOfAccounts


def _find_parent_chart_account():
    """Locate the header account under which bank accounts live."""
    for name in ("Bank Accounts", "Bank Account", "Bank"):
        try:
            return ChartOfAccounts.objects.get(name=name)
        except ChartOfAccounts.DoesNotExist:
            continue
        except DatabaseError:
            return None
    return None


def _next_child_code(parent):
    existing_children = ChartOfAccounts.objects.filter(code__startswith=parent.code).exclude(pk=parent.pk)
    existing_numbers = []
    for acc in existing_children:
        suffix = acc.code[len(parent.code):]
        if suffix.isdigit():
            existing_numbers.append(int(suffix))
    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    return f"{parent.code}{next_number:02d}"


def ensure_bank_chart_account(bank_account):
    """
    Make sure a ChartOfAccounts ledger is linked to the given bank account.

    Returns the ChartOfAccounts instance if available, otherwise None.
    """
    if bank_account.chart_account_id:
        return bank_account.chart_account

    parent = _find_parent_chart_account()
    if parent is None:
        return None

    account_name = f"{bank_account.bank.bank_name} - {bank_account.account_number}"
    try:
        coa = ChartOfAccounts.objects.filter(name__iexact=account_name).first()
        if coa is None:
            coa = ChartOfAccounts.objects.filter(description__icontains=bank_account.account_number).first()
        if coa is None:
            account_code = _next_child_code(parent)
            coa, _ = ChartOfAccounts.objects.get_or_create(
                code=account_code,
                defaults={
                    'name': account_name,
                    'type': 'asset',
                    'parent_id': parent.pk,
                    'is_header': False,
                    'active': bank_account.status,
                    'status': bank_account.status,
                    'description': f"Bank account for {bank_account.account_number} ({bank_account.bank.bank_name})",
                    'created_by_id': bank_account.created_by_id,
                },
            )
        if coa:
            bank_account.chart_account_id = coa.pk
            bank_account.save(update_fields=['chart_account'])
            return coa
    except DatabaseError:
        return None

    return None
