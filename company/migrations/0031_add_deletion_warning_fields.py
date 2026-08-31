from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0030_remove_company_credit_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='deletion_warning_email_count',
            field=models.IntegerField(
                default=0,
                help_text='Number of deletion warning emails sent (0-3, resets when license renewed)',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='deletion_warning_email_last_sent',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='When was the last deletion warning email sent?',
            ),
        ),
    ]
