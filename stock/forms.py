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


class StockAdjustmentForm(forms.Form):
    """Manually increase or decrease the stock of an item in a warehouse."""
    DIRECTION_CHOICES = [
        ('in', 'Add stock (increase)'),
        ('out', 'Remove stock (decrease)'),
    ]

    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    direction = forms.ChoiceField(
        choices=DIRECTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.DecimalField(
        min_value=Decimal('0.01'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for this adjustment (optional)'})
    )


class StockTransferForm(forms.Form):
    """Move a quantity of an item from one warehouse to another."""
    item = forms.ModelChoiceField(
        queryset=Item.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status=True),
        label="From warehouse",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    to_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status=True),
        label="To warehouse",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    quantity = forms.DecimalField(
        min_value=Decimal('0.01'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes (optional)'})
    )

    def clean(self):
        cleaned = super().clean()
        from_warehouse = cleaned.get('from_warehouse')
        to_warehouse = cleaned.get('to_warehouse')
        if from_warehouse and to_warehouse and from_warehouse == to_warehouse:
            raise forms.ValidationError("Source and destination warehouse must be different.")
        return cleaned
