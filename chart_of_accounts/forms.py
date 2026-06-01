from django import forms
from .models import ChartOfAccounts

class TypeModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name  # Show only the name, not code

class ChartOfAccountsForm(forms.ModelForm):
    type = TypeModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(code__regex=r'^\d$'),
        empty_label="Select Account Type",
        to_field_name='code',
        required=True,
        label="Account Type"
    )
    
    parent = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.none(),
        required=True,
    )
    search_code = forms.CharField(label='Account Code', required=False)
    class Meta:
        model = ChartOfAccounts
        fields = ['name', 'type', 'parent', 'description','search_code', 'is_header', 'active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If 'type' value is in POST or instance, filter parents accordingly
        if 'type' in self.data:
            try:
                type_code = self.data.get('type')
                self.fields['parent'].queryset = ChartOfAccounts.objects.filter(code__startswith=type_code)
            except (ValueError, TypeError):
                self.fields['parent'].queryset = ChartOfAccounts.objects.none()
        elif self.instance.pk:
            # When editing existing object, include relevant parents
            # type_code = self.instance.type.code if self.instance.type else None
            type_code = self.instance.type if self.instance.type else None
            if type_code:
                self.fields['parent'].queryset = ChartOfAccounts.objects.filter(code__startswith=type_code)
    # Make parent dropdown show only the name
        if 'parent' in self.fields:
            self.fields['parent'].label_from_instance = lambda obj: obj.name
    def clean_type(self):
        # Return the code string only to save in model
        type_obj = self.cleaned_data['type']
        if isinstance(type_obj, ChartOfAccounts):
            return type_obj.code
        return type_obj