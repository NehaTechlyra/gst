from django import forms
from django.contrib.auth.models import User
from .models import (
    Lead, Opportunity, Update, FollowUp, LostReason, PreSalesInteraction
)
from Items.models import Item
from HR.models import Employee
from django.contrib.auth.models import User as AuthUser


class LeadForm(forms.ModelForm):
    # Allow selecting multiple products. The Lead model currently stores
    # `product_interested` as a CharField, so we persist a comma-separated
    # list of Item names here for backward compatibility.
    product_interested = forms.ModelMultipleChoiceField(
        queryset=Item.objects.filter(sales_info=True, status=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'data-placeholder': 'Search product...', 'multiple': 'multiple'}),
        required=True,
        label='Product Interested'
    )
    # Show HR employees in Assigned Employee dropdown and persist Employee
    assigned_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
        required=False,
        label='Assigned Employee'
    )
    
    class Meta:
        model = Lead
        model = Lead
        # Do not include 'assigned_to' in model fields because the form
        # shows HR.Employee choices (Employee instances). The form-level
        # 'assigned_to' field maps Employee -> auth.User in save().
        fields = [
            'customer_name', 'phone', 'email', 'product_interested',
            'additional_info', 'source', 'priority', 'status', 'assigned_employee'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.Select(attrs={'class': 'form-control'}),
                'assigned_employee': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
                'priority': forms.Select(attrs={'class': 'form-control'}),
                'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        """Override save to convert selected Item objects to a comma-separated string and persist HR Employee"""
        instance = super().save(commit=False)
        # Convert selected Items to a comma-separated name string
        selected = self.cleaned_data.get('product_interested')
        if selected:
            # selected may be a QuerySet or list of Item instances
            names = [getattr(it, 'name', str(it)) for it in selected]
            # store as comma-separated names
            instance.product_interested = ', '.join(names)
        # Persist selected HR Employee
        emp = self.cleaned_data.get('assigned_employee')
        if emp and isinstance(emp, Employee):
            instance.assigned_employee = emp
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        """Prefill `product` from stored string when editing PreSalesInteraction.

        The PreSales model stores `product` as a string (Item.name). On edit,
        map that string back to an Item instance so the ModelChoiceField shows
        the previously-selected product. Also ensure the matched Item is in
        the field choices so the option renders for Select2.
        """
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        if instance and getattr(instance, 'product', None):
            prod_name = (instance.product or '').strip()
            if prod_name:
                item = Item.objects.filter(name__iexact=prod_name).first()
                if not item:
                    item = Item.objects.filter(name__icontains=prod_name).first()
                if item:
                    qs = self.fields['product'].queryset
                    other_choices = list(qs.values_list('pk', 'name'))
                    other_choices = [c for c in other_choices if c[0] != item.pk]
                    self.fields['product'].choices = [(item.pk, item.name)] + other_choices
                    self.fields['product'].initial = item.pk

    def __init__(self, *args, **kwargs):
        """Prefill `product_interested` from stored string when editing.

        The Lead model stores `product_interested` as a string (Item.name).
        On edit, convert that string back to an Item instance so the
        ModelChoiceField / Select2 shows the previously-selected product.
        """
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        if instance and getattr(instance, 'product_interested', None):
            prod_name = (instance.product_interested or '').strip()
            if prod_name:
                item = Item.objects.filter(name__iexact=prod_name).first()
                if not item:
                    item = Item.objects.filter(name__icontains=prod_name).first()
                if item:
                    qs = self.fields['product_interested'].queryset
                    other_choices = list(qs.values_list('pk', 'name'))
                    other_choices = [c for c in other_choices if c[0] != item.pk]
                    self.fields['product_interested'].choices = [(item.pk, item.name)] + other_choices
                    self.fields['product_interested'].initial = item.pk

    def __init__(self, *args, **kwargs):
        """Prefill `product` from stored string when editing PreSalesInteraction.

        The PreSales model stores `product` as a string (Item.name). On edit,
        map that string back to an Item instance so the ModelChoiceField shows
        the previously-selected product. Also ensure the matched Item is in
        the field choices so the option renders for Select2.
        """
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        if instance and getattr(instance, 'product', None):
            prod_name = (instance.product or '').strip()
            if prod_name:
                item = Item.objects.filter(name__iexact=prod_name).first()
                if not item:
                    item = Item.objects.filter(name__icontains=prod_name).first()
                if item:
                    qs = self.fields['product'].queryset
                    other_choices = list(qs.values_list('pk', 'name'))
                    other_choices = [c for c in other_choices if c[0] != item.pk]
                    self.fields['product'].choices = [(item.pk, item.name)] + other_choices
                    self.fields['product'].initial = item.pk

    def __init__(self, *args, **kwargs):
        """Prefill `product_interested` from stored string when editing.

        The Lead model stores `product_interested` as a string (Item.name).
        On edit, convert that string back to an Item instance so the
        ModelChoiceField / Select2 shows the previously-selected product.
        """
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        # If the existing Lead stored product_interested as a comma-separated
        # list of names, map them back to Item instances so the multiple
        # select shows the previously-chosen products.
        if instance and getattr(instance, 'product_interested', None):
            raw = (instance.product_interested or '').strip()
            if raw:
                # split on commas and strip whitespace
                names = [p.strip() for p in raw.split(',') if p.strip()]
                pks = []
                for name in names:
                    item = Item.objects.filter(name__iexact=name).first()
                    if not item:
                        item = Item.objects.filter(name__icontains=name).first()
                    if item:
                        pks.append(item.pk)
                if pks:
                    # Ensure the selected items appear in choices
                    qs = self.fields['product_interested'].queryset
                    other_choices = list(qs.values_list('pk', 'name'))
                    # move selected items to the front of choices so they render
                    selected_choices = [(i.pk, i.name) for i in Item.objects.filter(pk__in=pks)]
                    remaining = [c for c in other_choices if c[0] not in pks]
                    self.fields['product_interested'].choices = selected_choices + remaining
                    self.fields['product_interested'].initial = pks


class LeadLostForm(forms.Form):
    lost_reason = forms.ModelChoiceField(
        queryset=LostReason.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    new_reason = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Or add new reason'})
    )


class OpportunityForm(forms.ModelForm):
    # Show HR employees for assignment (persist Employee)
    assigned_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
        required=False,
        label='Assigned Employee'
    )
    class Meta:
        model = Opportunity
        model = Opportunity
        # 'assigned_employee' shown as Employee in the form; mapping to auth.User
        # is handled in OpportunityForm.save(). Include assigned_employee in fields
        fields = [
            'lead', 'estimated_deal_value', 'products_quantities',
            'expected_closing_date', 'negotiation_notes', 'competitor_info',
            'status', 'priority', 'assigned_employee'
        ]
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search lead...'}),
            'estimated_deal_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'products_quantities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expected_closing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'negotiation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'competitor_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assigned_employee': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
        }
    def save(self, commit=True):
        instance = super().save(commit=False)
        emp = self.cleaned_data.get('assigned_employee')
        if emp and isinstance(emp, Employee):
            instance.assigned_employee = emp
        if commit:
            instance.save()
        return instance


class UpdateForm(forms.ModelForm):
    class Meta:
        model = Update
        fields = ['lead', 'opportunity', 'quotation', 'update_type', 'description', 'attachment']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search lead...'}),
            'opportunity': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search opportunity...'}),
            'quotation': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search quotation...'}),
            'update_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class FollowUpForm(forms.ModelForm):
    assigned_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False,
        label='Assigned Employee'
    )
    class Meta:
        model = FollowUp
        # exclude model 'assigned_to' from automatic assignment so we can map
        # an HR.Employee to an auth.User manually in save()
        fields = ['lead', 'opportunity', 'quotation', 'description', 'followup_date', 'reminder_interval', 'assigned_employee']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search lead...'}),
            'opportunity': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search opportunity...'}),
            'quotation': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search quotation...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'followup_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'reminder_interval': forms.Select(attrs={'class': 'form-control'}),
            'assigned_employee': forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
        }
    def save(self, commit=True):
        instance = super().save(commit=False)
        emp = self.cleaned_data.get('assigned_employee')
        if emp and isinstance(emp, Employee):
            instance.assigned_employee = emp
        if commit:
            instance.save()
        return instance


class LostReasonForm(forms.ModelForm):
    class Meta:
        model = LostReason
        fields = ['reason']
        widgets = {
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PreSalesInteractionForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Item.objects.filter(sales_info=True, status=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search product...'}),
        required=False,
        label='Product'
    )
    assigned_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status=True),
        widget=forms.Select(attrs={'class': 'form-control select2', 'data-placeholder': 'Search employee...'}),
        required=False,
        label='Assigned Employee'
    )
    
    class Meta:
        model = PreSalesInteraction
        fields = [
            'lead', 'opportunity', 'customer_name', 'product', 'contact',
            'description', 'type', 'assigned_employee'
        ]
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Search lead...'}),
            'opportunity': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Search opportunity...'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'assigned_employee': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Search employee...'}),
        }
    
    def save(self, commit=True):
        """Override save to convert Item object to string and persist HR Employee"""
        instance = super().save(commit=False)
        # Convert Item object to its name string
        if isinstance(self.cleaned_data.get('product'), Item):
            instance.product = self.cleaned_data['product'].name
        # Persist selected HR Employee
        emp = self.cleaned_data.get('assigned_employee')
        if emp and isinstance(emp, Employee):
            instance.assigned_employee = emp
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        """Prefill `product` from stored string when editing PreSalesInteraction.

        Map the stored product name back to an Item (case-insensitive) so the
        ModelChoiceField shows the selected product in the edit form (Select2).
        """
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        if instance and getattr(instance, 'product', None):
            prod_name = (instance.product or '').strip()
            if prod_name:
                item = Item.objects.filter(name__iexact=prod_name).first()
                if not item:
                    item = Item.objects.filter(name__icontains=prod_name).first()
                if item:
                    qs = self.fields['product'].queryset
                    other_choices = list(qs.values_list('pk', 'name'))
                    other_choices = [c for c in other_choices if c[0] != item.pk]
                    self.fields['product'].choices = [(item.pk, item.name)] + other_choices
                    self.fields['product'].initial = item.pk






