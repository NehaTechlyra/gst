from django import forms
from .models import Warehouse

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            'warehouse_name',
            'code',
            'address',
            'warehouse_incharge',
            'contact_phone',
            'contact_email',
            'description',
            
            'is_default'

        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'description': forms.Textarea(attrs={'rows': 2, 'cols': 40}),
        }

class WarehouseFormModal(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['warehouse_name', 'address']  # Only these fields
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }