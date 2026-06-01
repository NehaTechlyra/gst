from django import forms
from django.forms import modelformset_factory
from .models import Stock
from warehouse.models import Warehouse
from Items.models import Item
from decimal import Decimal


class StockForm(forms.ModelForm):
    item = forms.ModelChoiceField(queryset=Item.objects.filter(status=True))
    class Meta:
        model = Stock
        fields = [
            'item',
            'quantity',
            'expiration_date',
        ]

        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '-999999999'  # Allow negative quantities for reductions
            }),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty == 0:
            raise forms.ValidationError("Quantity must be non-zero (positive to add, negative to reduce)")
        return qty

class WarehouseSelectForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(status=True))

StockFormSet = modelformset_factory(Stock, form=StockForm, extra=1)
