from django.db import migrations, models
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0010_customer_is_draft'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='credit_limit',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Maximum allowed outstanding sales amount for this customer',
                max_digits=15,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]