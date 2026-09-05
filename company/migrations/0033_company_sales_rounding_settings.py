from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0032_alter_company_deletion_warning_email_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="sales_rounding_method",
            field=models.CharField(
                choices=[
                    ("none", "No Rounding"),
                    ("whole", "Nearest Whole Number"),
                    ("increment", "Nearest Incremental Value"),
                ],
                default="none",
                help_text="Controls how sales transaction totals are rounded.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="sales_rounding_increment",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Increment used when sales rounding method is nearest incremental value.",
                max_digits=12,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="show_sales_rounding_adjustment",
            field=models.BooleanField(
                default=True,
                help_text="If enabled, show the sales rounding adjustment line in transaction totals.",
            ),
        ),
    ]
