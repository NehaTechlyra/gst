from django.db import migrations
from django.utils.timezone import make_aware
from datetime import datetime


def add_opening_balance_equity_and_fix_stock_adjustment(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    db = schema_editor.connection.alias

    # -------------------------------------------------------------------------
    # 1. Opening Balance Equity (unchanged from your original migration)
    # -------------------------------------------------------------------------
    equity = ChartOfAccounts.objects.using(db).filter(name="Equity").first()

    if equity:
        existing = ChartOfAccounts.objects.using(db).filter(
            name="Opening Balance Equity"
        ).first()

        if not existing:
            created_at = make_aware(
                datetime.strptime("2025-09-23 10:19:19.423034", "%Y-%m-%d %H:%M:%S.%f")
            )
            ChartOfAccounts.objects.using(db).create(
                code="501",
                name="Opening Balance Equity",
                type=5,
                description="",
                is_header=False,
                active=True,
                created_at=created_at,
                updated_at=created_at,
                parent=equity,
                status=True,
                search_code="",
                created_by=None,
                updated_by=None,
            )

    # -------------------------------------------------------------------------
    # 2. Fix Stock Adjustment — change from Expense (type 4) to Asset (type 1)
    #    and move parent from Stock Expenses → Stock Assets.
    #
    #    WHY: Stock Adjustment is a contra-asset that offsets Stock In Hand.
    #    Keeping it as type '4' (Expense) caused:
    #      - Fiscal year closing to incorrectly credit it (Cr Stock Adjustment 400)
    #      - Balance sheet to show a ₹400 gap (Assets ≠ Liabilities + Equity)
    #      - Opening balance carry-forward to skip it entirely
    #    As type '1' (Asset) under Stock Assets it:
    #      - Never gets touched by fiscal year closing
    #      - Appears on the balance sheet, naturally offsetting Stock In Hand
    #      - Is carried forward in opening balances automatically
    # -------------------------------------------------------------------------
    stock_assets = ChartOfAccounts.objects.using(db).filter(
        name="Stock Assets", status=True
    ).first()

    stock_adjustment = ChartOfAccounts.objects.using(db).filter(
        name="Stock Adjustment"
    ).first()

    if stock_adjustment:
        stock_adjustment.type = '1'
        if stock_assets:
            stock_adjustment.parent = stock_assets
        stock_adjustment.save(using=db)


def reverse_migration(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    db = schema_editor.connection.alias

    # Reverse Opening Balance Equity
    ChartOfAccounts.objects.using(db).filter(name="Opening Balance Equity").delete()

    # Reverse Stock Adjustment back to Expense under Stock Expenses
    stock_expenses = ChartOfAccounts.objects.using(db).filter(
        name="Stock Expenses", status=True
    ).first()

    stock_adjustment = ChartOfAccounts.objects.using(db).filter(
        name="Stock Adjustment"
    ).first()

    if stock_adjustment:
        stock_adjustment.type = '4'
        if stock_expenses:
            stock_adjustment.parent = stock_expenses
        stock_adjustment.save(using=db)


class Migration(migrations.Migration):

    dependencies = [
        ('chart_of_accounts', '0002_insert_default_acc1'),
    ]

    operations = [
        migrations.RunPython(
            add_opening_balance_equity_and_fix_stock_adjustment,
            reverse_migration,
        ),
    ]