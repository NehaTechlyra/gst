from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0048_purchasereturn_currency_snapshot'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseorderitem',
            name='price',
            field=models.DecimalField(decimal_places=4, max_digits=10),
        ),
        migrations.AlterField(
            model_name='purchaseorderitem',
            name='o_price',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.0000'), max_digits=12),
        ),
    ]
