from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ("sms_config", "0002_alter_smsconfiguration_usage_types"),
    ]

    operations = []
