from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PriceList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('price_type', models.CharField(choices=[('sales', 'Sales'), ('purchase', 'Purchase')], default='sales', max_length=10)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('rounding', models.CharField(choices=[('none', 'No Rounding'), ('nearest', 'Round to Nearest'), ('up', 'Round Up'), ('down', 'Round Down')], default='none', max_length=10)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'erp_price_lists', 'ordering': ['-created_at'], 'verbose_name': 'Price List', 'verbose_name_plural': 'Price Lists'},
        ),
        migrations.CreateModel(
            name='PriceListItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=255)),
                ('item_sku', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(blank=True, max_length=50, null=True)),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage (%)'), ('fixed', 'Fixed Amount'), ('custom', 'Custom Price')], default='percentage', max_length=15)),
                ('discount_value', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('custom_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('min_quantity', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('price_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_list_items', to='pricelists.pricelist')),
            ],
            options={'db_table': 'erp_price_list_items', 'ordering': ['item_name'], 'verbose_name': 'Price List Item', 'verbose_name_plural': 'Price List Items'},
        ),
        migrations.CreateModel(
            name='ContactPriceList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_name', models.CharField(max_length=255)),
                ('contact_type', models.CharField(choices=[('customer', 'Customer'), ('vendor', 'Vendor')], default='customer', max_length=10)),
                ('price_list', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_contacts', to='pricelists.pricelist')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'erp_contact_price_lists', 'verbose_name': 'Contact Price List', 'verbose_name_plural': 'Contact Price Lists'},
        ),
        migrations.AddConstraint(
            model_name='pricelistitem',
            constraint=models.UniqueConstraint(fields=['price_list', 'item_sku'], name='unique_pricelist_sku'),
        ),
    ]
