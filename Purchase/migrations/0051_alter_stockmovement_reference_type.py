from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0050_bill_tds_tcs_amount_bill_tds_tcs_definition_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockmovement',
            name='reference_type',
            field=models.CharField(
                choices=[
                    ('delivery_note', 'Delivery Note'),
                    ('delivery_note_reversal', 'Delivery Note Reversal'),
                    ('purchase_bill_payment', 'Purchase Bill Payment'),
                    ('purchase_return', 'Purchase Return'),
                    ('sales_order', 'Sales Order'),
                    ('adjustment', 'Manual Adjustment'),
                    ('transfer', 'Warehouse Transfer'),
                ],
                max_length=50,
            ),
        ),
    ]
