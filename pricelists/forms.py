from django import forms
from .models import PriceList, PriceListItem


class PriceListForm(forms.ModelForm):
    class Meta:
        model = PriceList
        fields = ['name', 'price_type', 'pricing_scheme', 'percentage_value', 'percentage_type', 'currency', 'description',
                  'is_active', 'rounding', 'valid_from', 'valid_to']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. VIP Customer Pricing',
            }),
            'price_type': forms.Select(attrs={'class': 'form-select'}),
            'pricing_scheme': forms.RadioSelect(),
            'percentage_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g. 10.00',
            }),
            'percentage_type': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'USD',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description...',
            }),
            'rounding': forms.Select(attrs={'class': 'form-select'}),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'valid_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        pricing_scheme = cleaned_data.get('pricing_scheme')
        percentage_value = cleaned_data.get('percentage_value')
        percentage_type = cleaned_data.get('percentage_type')

        if valid_from and valid_to and valid_to < valid_from:
            raise forms.ValidationError("Valid To date must be after Valid From date.")
        
        if pricing_scheme == 'percentage':
            if not percentage_value:
                self.add_error('percentage_value', "Percentage value is required for 'All Items (Percentage)' pricing scheme.")
            if not percentage_type:
                self.add_error('percentage_type', "Percentage type (Markup or Markdown) is required.")

        return cleaned_data


class PriceListItemForm(forms.ModelForm):
    class Meta:
        model = PriceListItem
        fields = ['item_name', 'item_sku', 'unit', 'base_price',
                  'discount_type', 'discount_value', 'custom_price', 'min_quantity', 'max_quantity']
        widgets = {
            'item_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item Name',
            }),
            'item_sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SKU-001',
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'pcs, kg, box...',
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'custom_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'min_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
            }),
            'max_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'No limit',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value', 0)
        custom_price = cleaned_data.get('custom_price')
        base_price = cleaned_data.get('base_price', 0)

        if discount_type == 'percentage' and discount_value and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        if discount_type == 'fixed' and discount_value and base_price and discount_value > base_price:
            raise forms.ValidationError("Fixed discount cannot exceed the base price.")
        if discount_type == 'custom' and not custom_price:
            raise forms.ValidationError("Custom price is required for 'Custom Price' discount type.")
        return cleaned_data
