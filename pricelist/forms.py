from django import forms
from .models import PriceList, PriceListItem, ContactPriceList


class PriceListForm(forms.ModelForm):
    class Meta:
        model = PriceList
        fields = [
            'name', 'type', 'description', 'currency',
            'rounding', 'valid_from', 'valid_to', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wholesale - Tier A'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD'}),
            'rounding': forms.Select(attrs={'class': 'form-select'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        if valid_from and valid_to and valid_from > valid_to:
            raise forms.ValidationError("'Valid From' date must be before 'Valid To' date.")
        return cleaned_data


class PriceListItemForm(forms.ModelForm):
    class Meta:
        model = PriceListItem
        fields = ['item', 'pricing_method', 'adjustment_type', 'percentage', 'custom_rate']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'pricing_method': forms.Select(attrs={'class': 'form-select', 'id': 'id_pricing_method'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'custom_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('pricing_method')
        if method == 'percentage':
            if not cleaned_data.get('percentage'):
                self.add_error('percentage', 'Percentage is required for this pricing method.')
            if not cleaned_data.get('adjustment_type'):
                self.add_error('adjustment_type', 'Adjustment type is required for percentage pricing.')
            cleaned_data['custom_rate'] = None
        elif method == 'fixed':
            if not cleaned_data.get('custom_rate'):
                self.add_error('custom_rate', 'Custom rate is required for fixed pricing.')
            cleaned_data['percentage'] = None
            cleaned_data['adjustment_type'] = None
        return cleaned_data


class ContactPriceListForm(forms.ModelForm):
    class Meta:
        model = ContactPriceList
        fields = ['contact', 'price_list']
        widgets = {
            'contact': forms.Select(attrs={'class': 'form-select'}),
            'price_list': forms.Select(attrs={'class': 'form-select'}),
        }
