# Generated migration for is_license_expired field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0004_licensekey_license_expired_email_last_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='licensekey',
            name='is_license_expired',
            field=models.BooleanField(
                default=False,
                help_text='Flag set to True at 12:00 AM on expiry date. Used for all expiry checks (emails, activation, etc.)'
            ),
        ),
    ]
