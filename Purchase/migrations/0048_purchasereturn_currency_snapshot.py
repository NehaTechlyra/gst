from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Purchase', '0047_bill_document_currency_bill_fx_rate_date_and_more'),
        ('currencies', '__first__'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasereturn',
            name='document_currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_returns', to='currencies.currency'),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='fx_rate_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='fx_rate_to_base',
            field=models.DecimalField(decimal_places=6, default=Decimal('1.000000'), help_text='Exchange rate from purchase return currency to company base currency.', max_digits=18),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='refund_amount_base',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=18),
        ),
    ]
