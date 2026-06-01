from django.db import migrations, models


def forwards(apps, schema_editor):
    Lead = apps.get_model('crm', 'Lead')
    Opportunity = apps.get_model('crm', 'Opportunity')
    FollowUp = apps.get_model('crm', 'FollowUp')
    Employee = apps.get_model('HR', 'Employee')
    User = apps.get_model('auth', 'User')
    
    db = schema_editor.connection.alias

    # Map existing assigned_to (User) -> assigned_employee (Employee) by email
    for lead in Lead.objects.using(db).filter(assigned_to__isnull=False):
        try:
            user = lead.assigned_to
            emp = Employee.objects.using(db).filter(email__iexact=user.email).first()
            if emp:
                lead.assigned_employee_id = emp.pk
                lead.save(update_fields=['assigned_employee'], using=db)
        except Exception:
            continue

    for opp in Opportunity.objects.using(db).filter(assigned_to__isnull=False):
        try:
            user = opp.assigned_to
            emp = Employee.objects.using(db).filter(email__iexact=user.email).first()
            if emp:
                opp.assigned_employee_id = emp.pk
                opp.save(update_fields=['assigned_employee'], using=db)
        except Exception:
            continue

    for fu in FollowUp.objects.using(db).filter(assigned_to__isnull=False):
        try:
            user = fu.assigned_to
            emp = Employee.objects.using(db).filter(email__iexact=user.email).first()
            if emp:
                fu.assigned_employee_id = emp.pk
                fu.save(update_fields=['assigned_employee'], using=db)
        except Exception:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_remove_quotation_created_by_remove_quotation_lead_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='assigned_employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='assigned_leads_employee', to='HR.employee'),
        ),
        migrations.AddField(
            model_name='opportunity',
            name='assigned_employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='assigned_opportunities_employee', to='HR.employee'),
        ),
        migrations.AddField(
            model_name='followup',
            name='assigned_employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='followups_employee', to='HR.employee'),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
