from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Items', '0005_item_min_stock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='selling_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='cost_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
    ]
