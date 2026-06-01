from django.db import migrations


def add_gst_treatments(apps, schema_editor):
    GstTreatment = apps.get_model('customer', 'GstTreatment')
    db = schema_editor.connection.alias  # Get the current database being migrated

    data = [
        (
            "Registered Business - Regular",
            "Business that is registered under GST"
        ),
        (
            "Registered Business - Composition",
            "Business that is registered under the Composition Scheme in GST"
        ),
        (
            "Unregistered Business",
            "Business that has not been registered under GST"
        ),
        (
            "Overseas",
            "Persons with whom you do import or export of supplies outside India"
        ),
        (
            "Special Economic Zone",
            "Business (Unit) that is located in a Special Economic Zone (SEZ) of India or a SEZ Developer"
        ),
        (
            "Deemed Export",
            "Supply of goods to an Export Oriented Unit or against Advanced Authorization/Export Promotion Capital Goods"
        ),
        (
            "Tax Deductor",
            "Departments of the State/Central government, governmental agencies or local authorities"
        ),
        (
            "SEZ Developer",
            "A person/organisation who owns at least 26% of the equity in creating business units in a Special Economic Zone (SEZ)"
        ),
    ]

    for name, description in data:
        GstTreatment.objects.using(db).get_or_create(
            name=name,
            defaults={"description": description}
        )


def remove_gst_treatments(apps, schema_editor):
    GstTreatment = apps.get_model('customer', 'GstTreatment')
    GstTreatment.objects.filter(
        name__in=[
            "Registered Business - Regular",
            "Registered Business - Composition",
            "Unregistered Business",
            "Overseas",
            "Special Economic Zone",
            "Deemed Export",
            "Tax Deductor",
            "SEZ Developer",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0006_customer_currency_customer_exemption_reason_and_more'),
    ]

    operations = [
        migrations.RunPython(add_gst_treatments, remove_gst_treatments),
    ]
