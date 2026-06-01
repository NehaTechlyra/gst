from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='registration_code',
            field=models.CharField(
                blank=True,
                help_text='Unique code for company-specific login URL',
                max_length=20,
                null=True,
                unique=True
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='db_created',
            field=models.BooleanField(
                default=False,
                help_text='Has the company database been created?'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='first_login_completed',
            field=models.BooleanField(
                default=False,
                help_text='Has the first login/database creation completed?'
            ),
        ),
    ]