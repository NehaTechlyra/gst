# Generated manually for recruitment phase 3

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HR', '0004_recruitmentoffer_phase2'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_candidates', to='HR.employee'),
        ),
        migrations.RemoveField(
            model_name='recruitmentoffer',
            name='appointment_message',
        ),
        migrations.RemoveField(
            model_name='recruitmentoffer',
            name='appointment_subject',
        ),
        migrations.AddField(
            model_name='recruitmentoffer',
            name='converted_to_employee_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
