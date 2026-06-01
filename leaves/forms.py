from django import forms
from .models import Leaves


class LeavesForm(forms.ModelForm):
    class Meta:
        model = Leaves
        fields = ['leave_name', 'days_allowed', 'status']
