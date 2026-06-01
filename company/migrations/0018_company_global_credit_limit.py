from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0017_company_terms_and_conditions'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='global_credit_limit',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Maximum allowed outstanding sales amount across customers',
                max_digits=15,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
