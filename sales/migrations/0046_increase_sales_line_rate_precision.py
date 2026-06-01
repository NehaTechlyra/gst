from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0045_sales_line_item_o_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesquotationitem',
            name='price',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name='salesquotationitem',
            name='o_price',
            field=models.DecimalField(decimal_places=6, default=Decimal('0.000000'), max_digits=18),
        ),
        migrations.AlterField(
            model_name='salesorderitem',
            name='price',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name='salesorderitem',
            name='o_price',
            field=models.DecimalField(decimal_places=6, default=Decimal('0.000000'), max_digits=18),
        ),
        migrations.AlterField(
            model_name='salesinvoiceitem',
            name='price',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name='salesinvoiceitem',
            name='o_price',
            field=models.DecimalField(decimal_places=6, default=Decimal('0.000000'), max_digits=18),
        ),
        migrations.AlterField(
            model_name='performainvoiceitem',
            name='price',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name='performainvoiceitem',
            name='o_price',
            field=models.DecimalField(decimal_places=6, default=Decimal('0.000000'), max_digits=18),
        ),
    ]
