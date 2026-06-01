from django import forms
from django.core.exceptions import ValidationError
from .models import FiscalYear, PeriodLockExemption


class FiscalYearForm(forms.ModelForm):
    """Form for creating and editing Fiscal Years"""
    
    class Meta:
        model = FiscalYear
        fields = ['name', 'start_date', 'end_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FY 2025-26',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
        }
    
    def clean(self):
        """Validate fiscal year dates"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError('Start date must be before end date.')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Fiscal Year Name'
        self.fields['start_date'].label = 'Start Date'
        self.fields['end_date'].label = 'End Date'
        self.fields['status'].label = 'Status'


class PeriodLockForm(forms.Form):
    """Form for locking/unlocking periods"""
    
    reason = forms.CharField(
        label='Reason',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Why are you locking/unlocking this period?'
        })
    )


class PeriodLockExemptionForm(forms.ModelForm):
    """Form for granting period lock exemptions"""
    
    class Meta:
        model = PeriodLockExemption
        fields = ['user', 'reason']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Why is this user exempted?'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label = 'User'
        self.fields['reason'].label = 'Exemption Reason'
