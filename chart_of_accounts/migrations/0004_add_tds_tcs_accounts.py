from datetime import datetime

from django.db import migrations
from django.utils.timezone import make_aware


def seed_tds_tcs_accounts(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    db = schema_editor.connection.alias

    created_at = make_aware(datetime.strptime("2025-09-23 10:19:19.423034", "%Y-%m-%d %H:%M:%S.%f"))

    parent_tax_assets = ChartOfAccounts.objects.using(db).filter(code="10207").first()
    parent_duties = ChartOfAccounts.objects.using(db).filter(code="20202").first()

    account_specs = [
        {
            "code": "1020711",
            "name": "TDS Receivable",
            "type": "1",
            "parent": parent_tax_assets,
            "description": "TDS withheld by customer and recoverable as tax credit",
        },
        {
            "code": "1020712",
            "name": "TCS Receivable",
            "type": "1",
            "parent": parent_tax_assets,
            "description": "TCS collected by supplier and recoverable as tax credit",
        },
        {
            "code": "2020212",
            "name": "TDS Payable",
            "type": "2",
            "parent": parent_duties,
            "description": "TDS withheld from supplier and payable to authorities",
        },
        {
            "code": "2020216",
            "name": "TCS Payable",
            "type": "2",
            "parent": parent_duties,
            "description": "TCS collected from customer and payable to authorities",
        },
    ]

    for spec in account_specs:
        ChartOfAccounts.objects.using(db).update_or_create(
            code=spec["code"],
            defaults={
                "name": spec["name"],
                "type": spec["type"],
                "parent": spec["parent"],
                "description": spec["description"],
                "is_header": False,
                "active": True,
                "status": True,
                "search_code": "",
                "created_at": created_at,
                "updated_at": created_at,
            },
        )


def reverse_seed_tds_tcs_accounts(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    db = schema_editor.connection.alias
    ChartOfAccounts.objects.using(db).filter(code__in=["1020711", "1020712", "2020216"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('chart_of_accounts', '0003_add_opening_balance_equity'),
    ]

    operations = [
        migrations.RunPython(seed_tds_tcs_accounts, reverse_seed_tds_tcs_accounts),
    ]
