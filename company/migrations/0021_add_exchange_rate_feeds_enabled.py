from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0020_alter_company_base_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='exchange_rate_feeds_enabled',
            field=models.BooleanField(default=False, help_text='When enabled, scheduled fetches will populate ExchangeRate rows from configured feeds'),
        ),
    ]
