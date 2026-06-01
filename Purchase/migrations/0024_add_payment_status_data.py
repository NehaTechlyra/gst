from django.db import migrations


def add_payment_status_data(apps, schema_editor):
    PaymentStatus = apps.get_model('Purchase', 'PaymentStatus')
    db = schema_editor.connection.alias

    statuses = [
        {'name': 'Not Paid'},
        {'name': 'Partially Paid'},
        {'name': 'Paid'},
    ]

    for status in statuses:
        PaymentStatus.objects.using(db).get_or_create(name=status['name'])


def remove_payment_status_data(apps, schema_editor):
    PaymentStatus = apps.get_model('Purchase', 'PaymentStatus')
    db = schema_editor.connection.alias
    PaymentStatus.objects.using(db).filter(
        name__in=['Not Paid', 'Partially Paid', 'Paid']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0023_alter_bill_payment_status'),  # 👈 update this
    ]

    operations = [
        migrations.RunPython(
            add_payment_status_data,
            reverse_code=remove_payment_status_data
        ),
    ]
