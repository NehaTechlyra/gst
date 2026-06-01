from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Purchase", "0045_alter_purchase_discount_values_decimal"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderitem",
            name="o_price",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
    ]
