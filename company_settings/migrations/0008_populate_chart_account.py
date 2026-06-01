from django.db import DatabaseError, migrations


def _find_parent_chart_account(ChartOfAccounts):
    for name in ("Bank Accounts", "Bank Account", "Bank"):
        try:
            return ChartOfAccounts.objects.get(name=name)
        except ChartOfAccounts.DoesNotExist:
            continue
        except DatabaseError:
            return None
    return None


def _chart_of_accounts_table_exists(connection):
    try:
        tables = connection.introspection.table_names()
    except DatabaseError:
        return False
    return 'chart_of_accounts' in tables


def _next_child_code(parent, ChartOfAccounts):
    existing_children = ChartOfAccounts.objects.filter(
        code__startswith=parent.code
    ).exclude(pk=parent.pk)

    existing_numbers = []
    for acc in existing_children:
        suffix = acc.code[len(parent.code):]
        if suffix.isdigit():
            existing_numbers.append(int(suffix))

    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    return f"{parent.code}{next_number:02d}"


def populate_chart_accounts(apps, schema_editor):
    connection = schema_editor.connection
    if not _chart_of_accounts_table_exists(connection):
        return

    CompanyBankAccount = apps.get_model('company_settings', 'CompanyBankAccount')
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')

    parent = _find_parent_chart_account(ChartOfAccounts)
    if parent is None:
        return

    for bank_account in CompanyBankAccount.objects.select_related('bank').all():
        if bank_account.chart_account_id:
            continue

        account_name = f"{bank_account.bank.bank_name} - {bank_account.account_number}"
        coa = ChartOfAccounts.objects.filter(name__iexact=account_name).first()
        if coa is None:
            coa = ChartOfAccounts.objects.filter(
                description__icontains=bank_account.account_number
            ).first()

        if coa is None:
            account_code = _next_child_code(parent, ChartOfAccounts)
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


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0007_companybankaccount_chart_account'),
        ('chart_of_accounts', '0002_insert_default_acc1'),
    ]

    operations = [
        migrations.RunPython(populate_chart_accounts, reverse_code=migrations.RunPython.noop),
    ]
