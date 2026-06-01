from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0044_purchaseorder_document_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billitem',
            name='prd_disvalue',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name='purchaseorderitem',
            name='prd_disvalue',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
    ]
