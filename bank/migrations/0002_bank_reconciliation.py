# Generated migration - Bank Reconciliation with CSV support and auto-matching

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company_settings', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BankReconciliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(help_text='Period start date')),
                ('end_date', models.DateField(help_text='Period end date')),
                ('closing_balance', models.DecimalField(decimal_places=2, help_text='Closing balance from bank statement', max_digits=15)),
                ('cleared_amount', models.DecimalField(decimal_places=2, default=0, help_text='Sum of ticked/cleared transactions (auto-calculated)', max_digits=15)),
                ('difference', models.DecimalField(decimal_places=2, default=0, help_text='Difference = closing_balance - cleared_amount', max_digits=15)),
                ('status', models.CharField(choices=[('In Progress', 'In Progress'), ('Reconciled', 'Reconciled')], default='In Progress', help_text="'In Progress' or 'Reconciled'", max_length=20)),
                ('attachment', models.FileField(blank=True, help_text='Optional bank statement or supporting document', null=True, upload_to='bank_reconciliation_attachments/')),
                ('reconciled_date', models.DateField(blank=True, help_text='Date when reconciliation was completed', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bank_account', models.ForeignKey(help_text='The bank account being reconciled', on_delete=django.db.models.deletion.CASCADE, related_name='reconciliations', to='company_settings.companybankaccount')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reconciliations_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bank Reconciliation',
                'verbose_name_plural': 'Bank Reconciliations',
                'ordering': ['-end_date'],
                'unique_together': {('bank_account', 'end_date')},
            },
        ),
        migrations.CreateModel(
            name='BankReconciliationLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_id', models.IntegerField(help_text='ID of the transaction (journal_entry ID, payment ID, etc.)')),
                ('transaction_type', models.CharField(choices=[('payment_received', 'Payment Received'), ('payment_made', 'Payment Made'), ('journal', 'Journal Entry'), ('manual', 'Manual Adjustment')], help_text='Type of transaction', max_length=30)),
                ('transaction_date', models.DateField(help_text='Date of the transaction')),
                ('description', models.CharField(blank=True, help_text='Description from the transaction', max_length=255)),
                ('reference', models.CharField(blank=True, help_text='Reference number (cheque #, invoice #, etc.)', max_length=100)),
                ('debit_amount', models.DecimalField(decimal_places=2, default=0, help_text='Debit amount (outflow)', max_digits=15)),
                ('credit_amount', models.DecimalField(decimal_places=2, default=0, help_text='Credit amount (inflow)', max_digits=15)),
                ('is_cleared', models.BooleanField(default=False, help_text='True = user ticked this transaction as cleared')),
                ('auto_matched', models.BooleanField(default=False, help_text='True = system auto-matched this to a statement line')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reconciliation', models.ForeignKey(help_text='Parent reconciliation', on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='bank.bankreconciliation')),
            ],
            options={
                'verbose_name': 'Reconciliation Line',
                'verbose_name_plural': 'Reconciliation Lines',
                'ordering': ['transaction_date'],
                'unique_together': {('reconciliation', 'transaction_id', 'transaction_type')},
            },
        ),
        migrations.CreateModel(
            name='BankStatementLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statement_date', models.DateField(help_text='Date of the transaction')),
                ('description', models.CharField(help_text='Description from the bank statement', max_length=255)),
                ('reference', models.CharField(blank=True, help_text='Reference from bank statement', max_length=100)),
                ('debit_amount', models.DecimalField(decimal_places=2, default=0, help_text='Debit amount (outflow)', max_digits=15)),
                ('credit_amount', models.DecimalField(decimal_places=2, default=0, help_text='Credit amount (inflow)', max_digits=15)),
                ('matched_transaction_id', models.IntegerField(blank=True, help_text='ID of matched system transaction (if any)', null=True)),
                ('match_status', models.CharField(choices=[('auto_matched', 'Auto Matched'), ('manually_matched', 'Manually Matched'), ('unmatched', 'Unmatched')], default='unmatched', help_text='Match status with system transactions', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bank_account', models.ForeignKey(help_text='Bank account this statement line belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='statement_lines', to='company_settings.companybankaccount')),
                ('reconciliation', models.ForeignKey(blank=True, help_text='Which reconciliation this was uploaded for', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='statement_lines', to='bank.bankreconciliation')),
            ],
            options={
                'verbose_name': 'Bank Statement Line',
                'verbose_name_plural': 'Bank Statement Lines',
                'ordering': ['statement_date'],
            },
        ),
        migrations.AddIndex(
            model_name='bankstatementline',
            index=models.Index(fields=['bank_account', 'statement_date'], name='bank_bankst_bank_ac_idx'),
        ),
        migrations.AddIndex(
            model_name='bankstatementline',
            index=models.Index(fields=['match_status'], name='bank_bankst_match_s_idx'),
        ),
    ]
