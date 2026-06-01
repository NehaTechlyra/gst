from django import forms
from .models import TaxGroup, Tax, TaxType, TaxMaster
from django.core.exceptions import ValidationError

class TaxTypeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name

class TaxTypeForm(forms.ModelForm):
    class Meta:
        model = TaxType
        fields = ['name']
        labels = {
            'name': 'Tax Type Name',
        }

class TaxForm(forms.ModelForm):
    tax_scope = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tax Scope',
        required=True,
    )
    def __init__(self, *args, **kwargs):
        show_optional_fields = kwargs.pop('show_optional_fields', True)
        company_tax_type = kwargs.pop('company_tax_type', None)  # ← add this
        self.company_tax_type = company_tax_type
        super().__init__(*args, **kwargs)
        self.fields.pop('status', None)
        
        # Always hide tax_type (structure) - always GST
        self.fields['tax_type'].widget = forms.HiddenInput()
        if not self.fields['tax_type'].initial:
            self.fields['tax_type'].initial = 'GST'
        
        # Always hide applicable_on - always Total Amount
        self.fields['applicable_on'].widget = forms.HiddenInput()
        if not self.fields['applicable_on'].initial:
            self.fields['applicable_on'].initial = 'Total Amount'
        
        if not show_optional_fields:
            self.fields.pop('name', None)
            self.fields.pop('country', None)

        # Hide tax_scope on edit; preserve existing value without exposing it.
        if self.instance.pk:
            self.fields.pop('tax_scope', None)
        elif company_tax_type and company_tax_type.upper() != 'SALES':
            # On create: Only SALES companies should see tax_scope
            self.fields.pop('tax_scope', None)

        if company_tax_type:
            ALLOWED_TAX_TYPES = {
                'GST':      [('GST', 'GST'),           ('LOCAL', 'Local Tax')],
                'VAT':      [('VAT', 'VAT'),           ('LOCAL', 'Local Tax')],
                'SALES':    [('SALES', 'Sales/Purchase Tax'),   ('LOCAL', 'Local Tax')],
                'TURNOVER': [('TURNOVER', 'Turnover Tax'), ('LOCAL', 'Local Tax')],
                'NONE':     [('NONE', 'None'),         ('LOCAL', 'Local Tax')],
            }
            allowed = ALLOWED_TAX_TYPES.get(company_tax_type.upper())
            if allowed and 'tax_type' in self.fields:
                self.fields['tax_type'].choices = allowed
                if not self.instance.pk:
                    self.fields['tax_type'].initial = allowed[0][0]



        self.fields['taxtype'] = TaxTypeChoiceField(
            queryset=self.fields['taxtype'].queryset,
            empty_label=self.fields['taxtype'].empty_label,
            required=self.fields['taxtype'].required,
        )
        self.fields['taxtype'].widget.attrs.update({
            'class': 'form-control select2-tax-type',
            'data-placeholder': 'Search tax type...',
        })
        if company_tax_type and company_tax_type.upper() != 'GST':
            # Hide and make not required for non-GST companies
            self.fields['taxtype'].required = False
            self.fields['taxtype'].widget = forms.HiddenInput()
        else:
            # GST — keep visible and required
            self.fields['taxtype'].required = True


        self.fields['tax_type'].widget.attrs.update({'class': 'form-control'})
        # Update tax_scope choices dynamically depending on company tax type
        # and the currently selected tax structure.
        if 'tax_scope' in self.fields:
            self.fields['tax_scope'].widget.attrs.update({'class': 'form-control'})
            # Determine current tax_type value (from bound data, initial, or instance)
            current_tax_type = ''
            try:
                # use self.data when form is bound
                if hasattr(self, 'data') and self.data:
                    # data keys may be prefixed (add_prefix), so try without prefix
                    current_tax_type = (self.data.get('tax_type') or self.data.get(self.add_prefix('tax_type')) or '')
                if not current_tax_type:
                    current_tax_type = (self.initial.get('tax_type') or getattr(self.instance, 'tax_type', '') or '')
            except Exception:
                current_tax_type = (self.initial.get('tax_type') or getattr(self.instance, 'tax_type', '') or '')

            current_tax_type = (str(current_tax_type) or '').upper()
            company_tt = (company_tax_type or '').upper()

            if company_tt == 'SALES' and current_tax_type == 'LOCAL':
                self.fields['tax_scope'].choices = [('', 'Select Scope'), ('BOTH', 'Both')]
            else:
                self.fields['tax_scope'].choices = [('', 'Select Scope')] + list(Tax.TAX_SCOPE_CHOICES)

            if not self.is_bound and not self.fields['tax_scope'].initial:
                for choice_value, _ in self.fields['tax_scope'].choices:
                    if choice_value:
                        self.fields['tax_scope'].initial = choice_value
                        break
        self.fields['rate'].widget.attrs.update({'class': 'form-control', 'step': '0.01'})
        # self.fields['tax_method'].widget.attrs.update({'class': 'form-control'})
        # self.fields['tax_order'].widget.attrs.update({'class': 'form-control'})
        # self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})


    class Meta:
        model = Tax
        fields = ['taxname', 'name', 'taxtype', 'tax_type', 'tax_scope', 'rate', 'applicable_on',  'country']
        labels = {
            'taxname': 'Tax Name',
            'name': 'Display Name',
            'taxtype': 'Tax Type',
            'tax_type': 'Tax Structure',
            'tax_scope': 'Tax Scope',
            'rate': 'Rate (%)',
            
            'applicable_on': 'Apply On',
            
            
            'country': 'Country',
        }
        def clean_tax_scope(self):
            tax_scope = self.cleaned_data.get('tax_scope')
            if not tax_scope:
                raise ValidationError('Please select a tax scope.')
            # Accept values defined in model choices
            allowed = [c[0] for c in Tax.TAX_SCOPE_CHOICES]
            # If company uses SALES and tax structure is LOCAL we also allow BOTH
            current_tax_type = self.cleaned_data.get('tax_type') or getattr(self.instance, 'tax_type', '')
            company_tt = (self.company_tax_type or '').upper()
            if company_tt == 'SALES' and str(current_tax_type).upper() == 'LOCAL':
                if 'BOTH' not in allowed:
                    allowed.append('BOTH')
            if tax_scope not in allowed:
                raise ValidationError('Select a valid choice. %s is not one of the available choices.' % tax_scope)
            return tax_scope
class TaxMasterForm(forms.ModelForm):
    tax_scope = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tax Scope',
        required=True,
    )
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Always hide and default tax_type to GST
        self.fields['tax_type'].widget = forms.HiddenInput()
        self.fields['tax_type'].initial = 'GST'
        
        # Always hide and default applicable_on to ALL
        self.fields['applicable_on'].widget = forms.HiddenInput()
        self.fields['applicable_on'].initial = 'ALL'
        
        self.fields['tax_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['tax_scope'].widget.attrs.update({'class': 'form-control'})
        self.fields['tax_rate'].widget.attrs.update({'class': 'form-control', 'step': '0.01'})
        # self.fields['tax_method'].widget.attrs.update({'class': 'form-control'})
        # self.fields['tax_order'].widget.attrs.update({'class': 'form-control'})
        # self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

        if self.company and self.company.tax_type:
            relevant_types = {
                'GST': ['GST', 'LOCAL'],
                'VAT': ['VAT', 'LOCAL'],
                'SALES': ['SALES', 'LOCAL'],
                'TURNOVER': ['TURNOVER', 'LOCAL'],
                'NONE': ['LOCAL'],
            }.get(self.company.tax_type, [choice[0] for choice in self.fields['tax_type'].choices])
            self.fields['tax_type'].choices = [choice for choice in self.fields['tax_type'].choices if choice[0] in relevant_types]

    class Meta:
        model = TaxMaster
        fields = ['tax_name', 'tax_type', 'tax_scope', 'tax_rate', 'applicable_on', ]
        labels = {
            'tax_name': 'Tax Name',
            'tax_type': 'Tax Type',
            'tax_scope': 'Tax Scope',
            'tax_rate': 'Tax Rate',
            
            'applicable_on': 'Apply On',
            
        }

    def clean_tax_scope(self):
        tax_scope = self.cleaned_data.get('tax_scope')
        if self.company and self.company.tax_type in ('TURNOVER', 'NONE') and tax_scope == 'ITEM':
            raise ValidationError('Item scope taxes are not allowed for TURNOVER or NONE tax types.')
        return tax_scope


class TaxGroupForm(forms.ModelForm):
    taxes = forms.ModelMultipleChoiceField(
        queryset=Tax.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Taxes"
    )

    class Meta:
        model = TaxGroup
        fields = ['group_name', 'taxes']

    def clean_taxes(self):
        taxes = self.cleaned_data.get('taxes')
        if taxes.count() < 1:
            raise ValidationError("You must select at least one tax.")
        return taxes
