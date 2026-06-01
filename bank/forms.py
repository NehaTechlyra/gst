from django import forms
from .models import Bank, BankReconciliation
from .models import BankRule
from datetime import date
from pathlib import Path


class BankForm(forms.ModelForm):
    class Meta:
        model = Bank
        fields = ['bank_name', 'status']


class ReconciliationStartForm(forms.ModelForm):
    """
    Form for starting a new reconciliation (Zoho Books style).
    User enters start_date, end_date, closing_balance and optional attachment.
    """

    class Meta:
        model = BankReconciliation
        fields = ['start_date', 'end_date', 'closing_balance', 'attachment']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True,
            }),
            'closing_balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'required': True,
                'placeholder': 'Closing balance from bank statement',
            }),
        'attachment': forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xls,.xlsx',
        }),
        }

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account
        # Make attachment optional at the form level
        self.fields['attachment'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if not start_date or not end_date:
            return cleaned_data

        # Validate date range
        if start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date.")

        if self.account:
            # Validate against previous reconciliation
            previous_recon = BankReconciliation.objects.filter(
                bank_account=self.account,
                status='Reconciled'
            ).order_by('-end_date').first()

            if previous_recon and start_date <= previous_recon.end_date:
                raise forms.ValidationError(
                    f"Start date cannot be before or equal to the previous reconciliation's "
                    f"end date ({previous_recon.end_date})."
                )

            # Prevent duplicate end_date for same account
            if end_date:
                exists = BankReconciliation.objects.filter(
                    bank_account=self.account,
                    end_date=end_date,
                ).exists()
                if exists:
                    raise forms.ValidationError(
                        "A reconciliation for this account with the same end date already exists."
                    )

        return cleaned_data


class BankStatementUploadForm(forms.Form):
    """Form for uploading bank statement files (CSV / Excel)"""

    statement_file = forms.FileField(
        label='Bank Statement File',
        help_text='Upload CSV or Excel for auto-matching transactions.',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xls,.xlsx',
        })
    )

    def clean_statement_file(self):
        file = self.cleaned_data.get('statement_file')
        allowed = ('.csv', '.xls', '.xlsx')

        if file:
            ext = Path(file.name).suffix.lower()
            if ext not in allowed:
                raise forms.ValidationError(
                    f"Unsupported file type '{ext}'. Please upload CSV, XLS or XLSX."
                )
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must not exceed 10 MB.")

        return file


class BankRuleForm(forms.ModelForm):
    class Meta:
        model = BankRule
        fields = ['name', 'pattern', 'amount_tolerance', 'date_window', 'active', 'auto_match']
        widgets = {
            'name':             forms.TextInput(attrs={'class': 'form-control'}),
            'pattern':          forms.TextInput(attrs={'class': 'form-control'}),
            'amount_tolerance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date_window':      forms.NumberInput(attrs={'class': 'form-control'}),
            'active':           forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_match':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
