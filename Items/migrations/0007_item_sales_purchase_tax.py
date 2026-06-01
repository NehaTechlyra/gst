from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("Tax", "0001_initial"),
        ("Items", "0006_increase_item_price_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="sales_tax",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="items_sales_tax",
                to="Tax.tax",
                verbose_name="Sales Tax Rate",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="purchase_tax",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="items_purchase_tax",
                to="Tax.tax",
                verbose_name="Purchase Tax Rate",
            ),
        ),
    ]

