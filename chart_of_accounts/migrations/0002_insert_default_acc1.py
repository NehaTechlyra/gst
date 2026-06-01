from django.db import migrations
from django.utils.timezone import make_aware
from datetime import datetime

def insert_default_chart_of_accounts(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    db = schema_editor.connection.alias
    # To avoid duplicate inserts if migration runs twice, you could check for entries before inserting if needed.

    # Raw data from CSV (id, code, name, type, description, is_header, active, created_at, parentid, status, search_code)
    raw_accounts = [
        (1, "1", "Asset", "", "What a company owns", True, True, "2025-09-23 09:47:54.206322", None, True, ""),
        (2, "2", "Liability", "", "What a company owes", True, True, "2025-09-23 09:47:54.211813", None, True, ""),
        (3, "3", "Income", "", "Revenue from sales", True, True, "2025-09-23 09:47:54.215994", None, True, ""),
        (4, "4", "Expenses", "", "Costs of doing business", True, True, "2025-09-23 09:47:54.220098", None, True, ""),
        (5, "5", "Equity", "", "The owners stake", True, True, "2025-09-23 09:47:54.223538", None, True, ""),
        (6, "101", "Fixed Assets", 1, "Costs of doing business", True, True, "2025-09-23 09:49:43.641957", 1, True, ""),
        (7, "102", "Current Assets", 1, "", True, True, "2025-09-23 10:18:29.413707", 1, True, ""),
        (8, "103", "Investments", 1, "", True, True, "2025-09-23 10:18:59.019747", 1, True, ""),
        (9, "104", "Temporary Accounts", 1, "", True, True, "2025-09-23 10:19:19.423034", 1, True, ""),
        (10, "201", "Capital Account", 2, "", True, True, "2025-09-23 10:19:19.423034", 2, True, ""),
        (11, "202", "Current Liabilities", 2, "", True, True, "2025-09-23 10:19:19.423034", 2, True, ""),
        (12, "301", "Direct Income", 3, "", True, True, "2025-09-23 10:19:19.423034", 3, True, ""),
        (13, "302", "Indirect Income", 3, "", True, True, "2025-09-23 10:19:19.423034", 3, True, ""),
        (14, "401", "Direct Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 4, True, ""),
        (15, "402", "Indirect Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 4, True, ""),
        (16, "10201", "Accounts Receivable", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (17, "10202", "Bank Accounts", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (18, "10203", "Cash In Hand", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (19, "10204", "Loans and Advances (Assets)", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (20, "10205", "Securities and Deposits", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (21, "10206", "Stock Assets", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (22, "10207", "Tax Assets", 1, "", True, True, "2025-09-23 10:19:19.423034", 7, True, ""),
        (23, "10101", "Accumulated Depreciations", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (24, "10102", "Buildings", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (25, "10103", "Capital Equipments", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (26, "10104", "Electronic Equipments", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (27, "10105", "Furnitures and Fixtures", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (28, "10106", "Office Equipments", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),
        (29, "10107", "Plants and Machineries", 1, "", True, True, "2025-09-23 10:19:19.423034", 6, True, ""),


        (30, "10401", "Temporary Opening", 1, "", True, True, "2025-09-23 10:19:19.423034", 9, True, ""),
        (31, "20101", "Reserves and Surplus", 2, "", True, True, "2025-09-23 10:19:19.423034", 10, True, ""),
        (32, "20102", "Revaluation Surplus", 2, "", True, True, "2025-09-23 10:19:19.423034", 10, True, ""),
        (33, "20103", "Shareholders Funds", 2, "", True, True, "2025-09-23 10:19:19.423034", 10, True, ""),
        (34, "20201", "Accounts Payable", 2, "", True, True, "2025-09-23 10:19:19.423034", 11, True, ""),
        (35, "20202", "Duties and Taxes", 2, "", True, True, "2025-09-23 10:19:19.423034", 11, True, ""),
        (36, "20203", "Loans (Liabilities)", 2, "", True, True, "2025-09-23 10:19:19.423034", 11, True, ""),
        (37, "20204", "Stock Liabilities", 2, "", True, True, "2025-09-23 10:19:19.423034", 11, True, ""),
        (38, "30101", "Sales", 3, "", True, True, "2025-09-23 10:19:19.423034", 12, True, ""),


        (39, "30102", "Service", 3, "", True, True, "2025-09-23 10:19:19.423034", 12, True, ""),
        (40, "40101", "Stock Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 14, True, ""),
        (41, "40201", "Administrative Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (42, "40202", "Commission on Sales", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (43, "40203", "Depreciation", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (44, "40204", "Entertainment Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (45, "40205", "Exchange Gain/Loss", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (46, "40206", "Freight and Forwarding Charges", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (47, "40207", "GST Expense", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (48, "40208", "Gain/Loss on Asset Disposal", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (49, "40209", "Impairment", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (50, "40210", "Legal Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),


        (51, "40211", "Marketing Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (52, "40212", "Miscellaneous Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (53, "40213", "Office Maintenance Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (54, "40214", "Office Rent", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (55, "40215", "Postal Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (56, "40216", "Print and Stationery", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (57, "40217", "Rounded Off", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (58, "40218", "Salary", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (59, "40219", "Sales Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (60, "40220", "Telephone Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),

        (61, "40221", "Travel Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (62, "40222", "Utility Expenses", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (63, "40223", "Write Off", 4, "", True, True, "2025-09-23 10:19:19.423034", 15, True, ""),
        (64, "1020101", "Debtors", 1, "", True, True, "2025-09-23 10:19:19.423034", 16, True, ""),
        (65, "1020201", "Bank Account", 1, "", True, True, "2025-09-23 10:19:19.423034", 17, True, ""),
        (66, "1020301", "Cash", 1, "", True, True, "2025-09-23 10:19:19.423034", 18, True, ""),
        (67, "1020501", "Earnest Money", 1, "", True, True, "2025-09-23 10:19:19.423034", 20, True, ""),
        (68, "1020601", "Stock In Hand", 1, "", True, True, "2025-09-23 10:19:19.423034", 21, True, ""),
        (69, "1020701", "Input Tax CGST", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),
        (70, "1020702", "Input Tax IGST", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),

        (71, "1020703", "Input Tax SGST", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),
        (72, "1020704", "Output Tax CGST Refund", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),
        (73, "1020705", "Output Tax IGST Refund", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),
        (74, "1020706", "Output Tax SGST Refund", 1, "", True, True, "2025-09-23 10:19:19.423034", 22, True, ""),
        (75, "2020101", "Creditors", 2, "", True, True, "2025-09-23 10:19:19.423034", 34, True, ""),
        (76, "2020102", "Payroll Payable", 2, "", True, True, "2025-09-23 10:19:19.423034", 34, True, ""),
        (77, "2020201", "Customs Duty Payable", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (78, "2020202", "Input Tax CGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (79, "2020203", "Input Tax IGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (80, "2020204", "Input Tax SGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),


        (81, "2020205", "Output Tax CGST", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (82, "2020206", "Output Tax CGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (83, "2020207", "Output Tax IGST", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (84, "2020208", "Output Tax IGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (85, "2020209", "Output Tax SGST", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (86, "2020210", "Output Tax SGST RCM", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (87, "2020211", "TDS", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (88, "2020212", "TDS Payable", 2, "", True, True, "2025-09-23 10:19:19.423034", 35, True, ""),
        (89, "2020301", "Bank Overdraft Account", 2, "", True, True, "2025-09-23 10:19:19.423034", 36, True, ""),
        (90, "2020302", "Secured Loans", 2, "", True, True, "2025-09-23 10:19:19.423034", 36, True, ""),
        
        (91, "2020303", "Unsecured Loans", 2, "", True, True, "2025-09-23 10:19:19.423034", 36, True, ""),
        (92, "2020401", "Stock Received But Not Billed", 2, "", True, True, "2025-09-23 10:19:19.423034", 37, True, ""),
        (93, "4010101", "Cost of Goods Sold", 4, "", True, True, "2025-09-23 10:19:19.423034", 40, True, ""),
        (94, "4010102", "Customs Duty Expense", 4, "", True, True, "2025-09-23 10:19:19.423034", 40, True, ""),
        (95, "4010103", "Expenses Included In Valuation", 4, "", True, True, "2025-09-23 10:19:19.423034", 40, True, ""),
        (96, "4010104", "Stock Adjustment", 1, "", True, True, "2025-09-23 10:19:19.423034", 21, True, ""),
        (97, "501", "Opening Balance Equity", 5, "", False, True, "2025-09-23 10:19:19.423034", 5, True, ""),

        # Add more entries following the same pattern extracted from CSV (or full list if desired)
    ]

    # A dict to map local CSV id to the created instance, to resolve parents
    instances = {}

    for acc in raw_accounts:
        acc_id, code, name, acc_type, description, is_header, active, created_at_str, parent_id, status, search_code = acc

        created_at = make_aware(datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S.%f"))

        parent_instance = instances.get(parent_id) if parent_id else None

        instance = ChartOfAccounts.objects.using(db).create(
            code=code,
            name=name,
            type=acc_type,
            description=description or '',
            is_header=is_header,
            active=active,
            created_at=created_at,
            updated_at=created_at,
            parent=parent_instance,
            status=status,
            search_code=search_code or '',
            created_by=None,
            updated_by=None,
        )
        instances[acc_id] = instance

def reverse_default_chart_of_accounts(apps, schema_editor):
    ChartOfAccounts = apps.get_model('chart_of_accounts', 'ChartOfAccounts')
    ChartOfAccounts.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('chart_of_accounts', '0001_initial'),  # Adjust if needed for your initial migration file name
    ]

    operations = [
        migrations.RunPython(insert_default_chart_of_accounts, reverse_default_chart_of_accounts),
    ]

