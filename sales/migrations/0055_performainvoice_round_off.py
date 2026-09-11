from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0054_salesquotation_round_off_salesorder_round_off"),
    ]

    operations = [
        migrations.AddField(
            model_name="performainvoice",
            name="round_off",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
            ),
        ),
    ]
