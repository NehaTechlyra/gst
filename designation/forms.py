from django import forms
from .models import Designations


class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designations
        fields = ['departments', 'designation_name', 'status']
