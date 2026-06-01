from django.db import migrations


def forwards(apps, schema_editor):
    Tax = apps.get_model('Tax', 'Tax')
    # Ensure we run the update against the current migration connection
    using_db = getattr(schema_editor, 'connection').alias
    Tax.objects.using(using_db).filter(tax_scope='BOTH').update(tax_scope='SALES')


class Migration(migrations.Migration):

    dependencies = [
        ('Tax', '0005_remove_taxtype_country_tax_applicable_on_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
