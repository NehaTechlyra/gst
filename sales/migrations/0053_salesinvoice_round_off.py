from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0052_alter_salesinvoice_payment_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesinvoice",
            name="round_off",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
            ),
        ),
    ]