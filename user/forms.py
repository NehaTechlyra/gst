from django import forms
from .models import User
from .models import Role
from django.contrib.auth.hashers import make_password
from HR.models import Employee
import re

class userForm(forms.ModelForm):
    confirm_pwd = forms.CharField(  # Added missing confirm_pwd field
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        max_length=128,
        required=True
    )


    usr_fname = forms.ModelChoiceField(  # change from CharField to ModelChoiceField
        queryset=Employee.objects.all(),
        label="Employee",
        widget=forms.Select(attrs={'class': 'form-control select2'}),  # for searchable dropdown
        required=False
    )


    class Meta:
        model = User
        fields = ['usr_name', 'usr_pwd', 'usr_fname', 'usr_mail', 'usr_phn', 'usr_rmrks', 'usr_roleid']
        labels = {
            'usr_name': 'User Name',
            'usr_pwd': 'Password',
            'usr_fname': 'Full Name',
            'usr_mail': 'Mail',
            'usr_phn': 'Phone No.',
            'usr_rmrks': 'Remarks',
            'usr_roleid': 'Role',
        }
        widgets = {
            'usr_pwd': forms.PasswordInput(attrs={'class': 'form-control'}),
            'usr_roleid': forms.Select(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        db_alias = kwargs.pop('db_alias', 'default')
        super().__init__(*args, **kwargs)
        self.fields['usr_roleid'].queryset = Role.objects.using(db_alias).all()
        self.fields['usr_fname'].queryset = Employee.objects.using(db_alias).all()
        self.fields['usr_roleid'].empty_label = "Select a role"
        self.fields['usr_fname'].empty_label = "Select employee"
        # Ensure consistent Bootstrap styling without relying on widget_tweaks
        for name, field in self.fields.items():
            # Skip fields that already set password widget or select2 class
            widget = field.widget
            existing_classes = widget.attrs.get('class', '')
            if 'form-control' not in existing_classes:
                widget.attrs['class'] = (existing_classes + ' form-control').strip()

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('usr_pwd')
        confirm_pwd = cleaned_data.get('confirm_pwd')
        if pwd and confirm_pwd and pwd != confirm_pwd:
            self.add_error('confirm_pwd', "Passwords do not match!")
        return cleaned_data
    def clean_usr_phn(self):
        phone = self.cleaned_data.get('usr_phn', '')
        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number should only contain digits!") [web:22]
        return phone
    
    def clean_usr_fname(self):
        data = self.cleaned_data.get('usr_fname')  # Use .get() since now optional
        if data:  # Only validate if provided

        # data = self.cleaned_data['usr_fname']
            if Employee.objects.filter(first_name=data).exists():  # use correct field
                raise forms.ValidationError("Employee with this first name already exists")
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Hash the password only if it's new or has changed
        if self.cleaned_data.get('usr_pwd'):
            instance.usr_pwd = make_password(self.cleaned_data['usr_pwd'])
        
        if commit:
            instance.save()
        return instance

class userEditForm(forms.ModelForm):
    class Meta:
        model = User
        # Include all fields except 'usr_pwd' as password changes handled separately
        fields = ['usr_name', 'usr_fname', 'usr_mail', 'usr_phn', 'usr_rmrks', 'usr_roleid']
        labels = {
            'usr_name': 'User Name',
            'usr_fname': 'Full Name',
            'usr_mail': 'Mail',
            'usr_phn': 'Phone No.',
            'usr_rmrks': 'Remarks',
            'usr_roleid': 'Role',
        }
        widgets = {
            'usr_roleid': forms.Select(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        db_alias = kwargs.pop('db_alias', 'default')
        super().__init__(*args, **kwargs)
        self.fields['usr_roleid'].queryset = Role.objects.using(db_alias).all()
        self.fields['usr_fname'].queryset = Employee.objects.using(db_alias).all()
        self.fields['usr_roleid'].empty_label = "Select a role"
        # Add form-control class to all widgets so templates don't need widget_tweaks
        for name, field in self.fields.items():
            widget = field.widget
            existing_classes = widget.attrs.get('class', '')
            if 'form-control' not in existing_classes:
                widget.attrs['class'] = (existing_classes + ' form-control').strip()

class PasswordUpdateForm(forms.Form):
    usr_pwd = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        max_length=128
    )
    confirm_pwd = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        max_length=128
    )

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('usr_pwd')
        confirm_pwd = cleaned_data.get('confirm_pwd')
        if pwd and confirm_pwd and pwd != confirm_pwd:
            self.add_error('confirm_pwd', "Passwords do not match!")
    
class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        # Only allow editing role fields; timestamps are set automatically
        fields = ['role_name', 'description']
        widgets = {
            'role_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
