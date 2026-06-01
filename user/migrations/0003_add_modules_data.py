# Generated migration for adding module permissions data
# Created: January 27, 2026

from django.db import migrations


def add_modules_data(apps, schema_editor):
    """Add all module permissions to the database"""
    Module = apps.get_model('user', 'Module')

    modules = [
        {'id': 51, 'name': 'Accounts Chart of Accounts'},
        {'id': 52, 'name': 'Accounts Journal'},
        {'id': 49, 'name': 'CRM Dashboard'},
        {'id': 46, 'name': 'CRM Follow Ups'},
        {'id': 44, 'name': 'CRM Lead'},
        {'id': 47, 'name': 'CRM Lost reason'},
        {'id': 45, 'name': 'CRM Opportunity'},
        {'id': 48, 'name': 'CRM Presale'},
        {'id': 25, 'name': 'HR Dashboard'},
        {'id': 26, 'name': 'HR Employee'},
        {'id': 27, 'name': 'HR masters'},
        {'id': 28, 'name': 'HR Recruitments'},
        {'id': 60, 'name': 'Masters Brand'},
        {'id': 80, 'name': 'Masters Category'},
        {'id': 36, 'name': 'Masters Customer'},
        {'id': 35, 'name': 'Masters Items'},
        {'id': 65, 'name': 'Masters Payment Terms'},
        {'id': 64, 'name': 'Masters Stock'},
        {'id': 59, 'name': 'Masters Taxes'},
        {'id': 81, 'name': 'Masters Type'},
        {'id': 61, 'name': 'Masters Unit'},
        {'id': 58, 'name': 'Masters User Roles'},
        {'id': 57, 'name': 'Masters Users'},
        {'id': 62, 'name': 'Masters vendor'},
        {'id': 63, 'name': 'Masters Warehouse'},
        {'id': 73, 'name': 'Purchase Bills'},
        {'id': 76, 'name': 'Purchase Delivery'},
        {'id': 75, 'name': 'Purchase Expenses'},
        {'id': 72, 'name': 'Purchase Order'},
        {'id': 74, 'name': 'Purchase Payments Made'},
        {'id': 53, 'name': 'Reports Balance Sheet'},
        {'id': 54, 'name': 'Reports Profit and Loss'},
        {'id': 55, 'name': 'Reports Trial Balance'},
        {'id': 78, 'name': 'Reports Cash Flow'},
        {'id': 77, 'name': 'Sales Delivery'},
        {'id': 50, 'name': 'Sales Invoice'},
        {'id': 11, 'name': 'Sales Orders'},
        {'id': 56, 'name': 'Sales Payments Received'},
        {'id': 37, 'name': 'Sales Quotation'},
        {'id': 82, 'name': 'Sales Return'},
        {'id': 84, 'name': 'Sales Performa Invoice'},
        {'id': 71, 'name': 'System settings'},
        {'id': 66, 'name': 'System settings Company'},
        {'id': 67, 'name': 'System settings Email Configuration'},
        {'id': 68, 'name': 'System settings Email Templates'},
        {'id': 69, 'name': 'System settings SMS Configuration'},
        {'id': 70, 'name': 'System settings SMS Templates'},
        {'id': 79, 'name': 'System settings Period Lock'},
        {'id': 88, 'name': 'System settings Other'},
    ]

    for module_data in modules:
        Module.objects.update_or_create(
            id=module_data['id'],
            defaults={'name': module_data['name']}
        )


def remove_modules_data(apps, schema_editor):
    """Remove all added module permissions (reverse migration)"""
    Module = apps.get_model('user', 'Module')
    
    module_ids = [
        51, 52, 49, 46, 44, 47, 45, 48, 25, 26, 27, 28,
        60, 80, 36, 35, 65, 64, 59, 81, 61, 58, 57, 62, 63,
        73, 76, 75, 72, 74, 53, 54, 55, 78, 77, 50, 11, 56, 37,
        71, 66, 67, 68, 69, 70, 79, 82, 84, 88
    ]
    
    Module.objects.filter(id__in=module_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_role_company'),
    ]

    operations = [
        migrations.RunPython(
            add_modules_data,
            reverse_code=remove_modules_data
        ),
    ]
