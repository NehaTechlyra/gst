from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0053_salesinvoice_round_off"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesquotation",
            name="round_off",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="round_off",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
            ),
        ),
    ]
