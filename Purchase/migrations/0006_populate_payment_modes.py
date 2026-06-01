from django.db import migrations

def populate_payment_modes(apps, schema_editor):
    PaymentMode = apps.get_model('Purchase', 'PaymentMode')  # Replace 'yourapp' with your app name
    db = schema_editor.connection.alias
    
    payment_modes = [
        'Cash',
        'Credit Card',
        'Debit Card',
        'Bank Transfer',
        'UPI',
        'Cheque',
        'Net Banking',
    ]
    
    for mode_name in payment_modes:
        PaymentMode.objects.using(db).get_or_create(name=mode_name)

def reverse_populate(apps, schema_editor):
    PaymentMode = apps.get_model('Purchase', 'PaymentMode')
    db = schema_editor.connection.alias
    PaymentMode.objects.using(db).all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0005_paymentmode_alter_bill_status'),  # Replace with your previous migration
    ]

    operations = [
        migrations.RunPython(populate_payment_modes, reverse_populate),
    ]