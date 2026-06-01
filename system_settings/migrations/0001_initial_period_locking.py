# Generated migration for Period Locking feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FiscalYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Fiscal Year name (e.g. FY 2025-26)', max_length=50, unique=True)),
                ('start_date', models.DateField(help_text='Fiscal year start date (e.g., 01 Apr 2025)')),
                ('end_date', models.DateField(help_text='Fiscal year end date (e.g., 31 Mar 2026)')),
                ('status', models.CharField(choices=[('active', 'Active'), ('closed', 'Closed'), ('archived', 'Archived')], default='active', help_text='Active = Current FY | Closed = Locked from edits | Archived = Historical', max_length=20)),
                ('is_locked', models.BooleanField(default=False, help_text='🔒 When TRUE: Prevents ALL edits (bills, items, journal, stock). View-only mode.')),
                ('lock_date', models.DateTimeField(blank=True, help_text='When was this fiscal year locked?', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fiscal_years_created', to=settings.AUTH_USER_MODEL)),
                ('locked_by', models.ForeignKey(blank=True, help_text='User who locked this fiscal year', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='locked_fiscal_years', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Fiscal Year',
                'verbose_name_plural': 'Fiscal Years',
                'db_table': 'system_settings_fiscalyear',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='PeriodLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('lock', 'Locked'), ('unlock', 'Unlocked')], help_text='Action performed: Lock or Unlock', max_length=10)),
                ('performed_at', models.DateTimeField(auto_now_add=True, help_text='When was this action performed?')),
                ('reason', models.TextField(blank=True, help_text='Why was this period locked/unlocked?', null=True)),
                ('fiscal_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lock_history', to='system_settings.fiscalyear')),
                ('performed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='period_lock_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Period Lock History',
                'verbose_name_plural': 'Period Lock Histories',
                'db_table': 'system_settings_periodlock',
                'ordering': ['-performed_at'],
            },
        ),
        migrations.CreateModel(
            name='PeriodLockExemption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(blank=True, help_text='Why is this user exempted from period locking?')),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('fiscal_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exemptions', to='system_settings.fiscalyear')),
                ('granted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='period_exemptions_granted', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='period_lock_exemptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Period Lock Exemption',
                'verbose_name_plural': 'Period Lock Exemptions',
                'db_table': 'system_settings_periodlockexemption',
                'unique_together': {('fiscal_year', 'user')},
            },
        ),
        migrations.AddIndex(
            model_name='fiscalyear',
            index=models.Index(fields=['-start_date'], name='system_sett_start_d_idx'),
        ),
        migrations.AddIndex(
            model_name='fiscalyear',
            index=models.Index(fields=['is_locked'], name='system_sett_is_lock_idx'),
        ),
    ]
