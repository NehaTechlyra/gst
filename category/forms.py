from django import forms
from .models import Category, Subcategory


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name']


class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['category', 'subcategory_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(status=True).order_by('category_name')
        self.fields['category'].empty_label = 'Select Category'
