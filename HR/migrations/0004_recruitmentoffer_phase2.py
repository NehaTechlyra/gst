# Generated manually for recruitment phase 2

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HR', '0003_jobopening_candidate_candidatestatushistory'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='current_status',
            field=models.CharField(
                choices=[
                    ('applied', 'Applied'),
                    ('screening', 'Screening'),
                    ('shortlisted', 'Shortlisted'),
                    ('interview_scheduled', 'Interview Scheduled'),
                    ('interviewed', 'Interviewed'),
                    ('selected', 'Selected'),
                    ('offer_sent', 'Offer Sent'),
                    ('offer_accepted', 'Offer Accepted'),
                    ('offer_declined', 'Offer Declined'),
                    ('joined', 'Joined'),
                    ('rejected', 'Rejected'),
                    ('hold', 'Hold'),
                ],
                default='applied',
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='candidatestatushistory',
            name='new_status',
            field=models.CharField(
                choices=[
                    ('applied', 'Applied'),
                    ('screening', 'Screening'),
                    ('shortlisted', 'Shortlisted'),
                    ('interview_scheduled', 'Interview Scheduled'),
                    ('interviewed', 'Interviewed'),
                    ('selected', 'Selected'),
                    ('offer_sent', 'Offer Sent'),
                    ('offer_accepted', 'Offer Accepted'),
                    ('offer_declined', 'Offer Declined'),
                    ('joined', 'Joined'),
                    ('rejected', 'Rejected'),
                    ('hold', 'Hold'),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name='RecruitmentOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('offered_ctc', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('joining_date', models.DateField(blank=True, null=True)),
                ('reporting_manager', models.CharField(blank=True, max_length=150, null=True)),
                ('offer_date', models.DateField(default=django.utils.timezone.now)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('email_to', models.EmailField(blank=True, max_length=254, null=True)),
                ('appointment_subject', models.CharField(blank=True, max_length=255, null=True)),
                ('appointment_message', models.TextField(blank=True, null=True)),
                ('response_notes', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='HR.candidate')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recruitment_offers_created', to=settings.AUTH_USER_MODEL)),
                ('job_opening', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='HR.jobopening')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recruitment_offers_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
