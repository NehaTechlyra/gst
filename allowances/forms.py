from django import forms
from .models import Allowances


class AllowancesForm(forms.ModelForm):
    class Meta:
        model = Allowances
        fields = ['allowance_name', 'amount', 'status']
