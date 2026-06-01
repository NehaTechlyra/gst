from django.db import migrations

def add_tax_types(apps, schema_editor):
    TaxType = apps.get_model('Tax', 'TaxType')
    db_alias = schema_editor.connection.alias  # ✅ gets the current company db
    TaxType.objects.using(db_alias).bulk_create([
        TaxType(name='SGST'),
        TaxType(name='CGST'),
        TaxType(name='IGST'),
    ])

class Migration(migrations.Migration):
    dependencies = [
        ('Tax', '0005_remove_taxtype_country_tax_applicable_on_and_more'),
    ]
    operations = [
        migrations.RunPython(add_tax_types),
    ]