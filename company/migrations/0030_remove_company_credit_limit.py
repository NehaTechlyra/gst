from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0029_company_print_paper_size'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='credit_limit',
        ),
    ]