# Generated manually for recruitment phase 1

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('department', '0001_initial'),
        ('designation', '0001_initial'),
        ('HR', '0002_delete_employeeidproof'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JobOpening',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('employment_type', models.CharField(choices=[('permanent', 'Permanent'), ('temporary', 'Temporary'), ('contract', 'Contract'), ('internship', 'Internship')], default='permanent', max_length=20)),
                ('vacancies', models.PositiveIntegerField(default=1)),
                ('work_location', models.CharField(blank=True, max_length=150, null=True)),
                ('hiring_manager', models.CharField(blank=True, max_length=150, null=True)),
                ('salary_min', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('salary_max', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('required_experience_years', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('required_skills', models.TextField(blank=True, null=True)),
                ('description', models.TextField()),
                ('opening_date', models.DateField(default=django.utils.timezone.now)),
                ('closing_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open'), ('on_hold', 'On Hold'), ('closed', 'Closed')], default='draft', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings_created', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings', to='department.department')),
                ('designation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings', to='designation.designations')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_openings_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('source', models.CharField(choices=[('referral', 'Referral'), ('website', 'Website'), ('linkedin', 'LinkedIn'), ('indeed', 'Indeed'), ('consultant', 'Consultant'), ('walk_in', 'Walk-in'), ('other', 'Other')], default='website', max_length=20)),
                ('current_company', models.CharField(blank=True, max_length=150, null=True)),
                ('current_ctc', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('expected_ctc', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('notice_period_days', models.PositiveIntegerField(blank=True, null=True)),
                ('total_experience_years', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('key_skills', models.TextField(blank=True, null=True)),
                ('resume_base64', models.TextField(blank=True, null=True)),
                ('resume_name', models.CharField(blank=True, max_length=255, null=True)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('current_status', models.CharField(choices=[('applied', 'Applied'), ('screening', 'Screening'), ('shortlisted', 'Shortlisted'), ('interview_scheduled', 'Interview Scheduled'), ('interviewed', 'Interviewed'), ('selected', 'Selected'), ('rejected', 'Rejected'), ('hold', 'Hold')], default='applied', max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidates_created', to=settings.AUTH_USER_MODEL)),
                ('job_opening', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidates', to='HR.jobopening')),
                ('recruiter_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recruitment_candidates', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidates_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CandidateStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_status', models.CharField(blank=True, max_length=30, null=True)),
                ('new_status', models.CharField(choices=[('applied', 'Applied'), ('screening', 'Screening'), ('shortlisted', 'Shortlisted'), ('interview_scheduled', 'Interview Scheduled'), ('interviewed', 'Interviewed'), ('selected', 'Selected'), ('rejected', 'Rejected'), ('hold', 'Hold')], max_length=30)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='HR.candidate')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidate_status_changes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-changed_at'],
            },
        ),
    ]
