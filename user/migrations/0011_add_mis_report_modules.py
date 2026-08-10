from django.db import migrations


def add_mis_report_modules(apps, schema_editor):
    Module = apps.get_model('user', 'Module')
    modules = [
        {'name': 'MIS Dashboard'},
        {'name': 'MIS Sales Report'},
        {'name': 'MIS Purchase Report'},
        {'name': 'MIS Inventory Report'},
        {'name': 'MIS Finance Report'},
        {'name': 'MIS CRM Report'},
        {'name': 'MIS HR Report'},
        {'name': 'MIS Expense Report'},
        {'name': 'MIS Export'},
    ]
    for module_data in modules:
        Module.objects.get_or_create(name=module_data['name'])


def remove_mis_report_modules(apps, schema_editor):
    Module = apps.get_model('user', 'Module')
    names = [
        'MIS Dashboard',
        'MIS Sales Report',
        'MIS Purchase Report',
        'MIS Inventory Report',
        'MIS Finance Report',
        'MIS CRM Report',
        'MIS HR Report',
        'MIS Expense Report',
        'MIS Export',
    ]
    Module.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0010_user_company_scoped_identity_constraints'),
    ]

    operations = [
        migrations.RunPython(add_mis_report_modules, reverse_code=remove_mis_report_modules),
    ]
