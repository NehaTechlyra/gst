from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0033_salesinvoice_payment_status_no_hardcoded_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoice',
            name='fx_rate_to_base',
            field=models.DecimalField(
                decimal_places=6,
                default=1.0,
                help_text='Exchange rate from invoice currency to company base currency.',
                max_digits=18,
            ),
        ),
    ]
