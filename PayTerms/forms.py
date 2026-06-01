from django import forms
from .models import PayTerms

class PayTermsForm(forms.ModelForm):
    class Meta:
        model = PayTerms
        exclude = ['created_by', 'updated_by','status','is_active']
        