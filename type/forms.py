from django import forms
from .models import Type
from category.models import Subcategory


class TypeForm(forms.ModelForm):
    class Meta:
        model = Type
        fields = ['subcategory', 'type_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcategory'].queryset = (
            Subcategory.objects.filter(status=True, category__status=True)
            .select_related('category')
            .order_by('category__category_name', 'subcategory_name')
        )
        self.fields['subcategory'].empty_label = 'Select Subcategory'
        self.fields['subcategory'].required = True
