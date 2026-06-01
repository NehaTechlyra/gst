from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Tax', '0008_alter_taxmaster_tax_type'),
        ('sales', '0019_alter_invpayment_payment_mode_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoice',
            name='turnover_tax',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sales_invoices_turnover_tax',
                to='Tax.tax',
            ),
        ),
    ]

