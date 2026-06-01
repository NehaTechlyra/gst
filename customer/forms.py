from django import forms
from .models import Customer,GstTreatment
from PayTerms.models import PayTerms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from currencies.models import Currency
from location_utils import configure_location_fields


NEW_CURRENCY_VALUE = "__new_currency__"
NEW_CURRENCY_LABEL = "+ New Currency"


def _append_new_currency_choice(field):

    print("_append_new_currency_choice called")
    # Shared JS turns this sentinel into a "create currency" flow.
    choices = list(field.choices)
    if not any(str(choice[0]) == NEW_CURRENCY_VALUE for choice in choices):
        choices.append((NEW_CURRENCY_VALUE, NEW_CURRENCY_LABEL))
        field.choices = choices

class CustomerForm(forms.ModelForm):
    
    payment_terms = forms.ModelChoiceField(
        queryset=PayTerms.objects.filter(is_active=True, status=True),
        required=False,
        empty_label="Select payment terms",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    country = CountryField(blank=False).formfield(
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    shipping_country = CountryField(blank=True).formfield(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    gst_treatment = forms.ModelChoiceField(
        queryset=GstTreatment.objects.all(),
        required=False,
        empty_label="Select a GST treatment",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    class Meta:
        model = Customer
        fields = [
            'customer_code', 'customer_type', 'first_name', 'last_name', 'company_name',
            'email', 'phone', 'mobile','gst_treatment','pan_number',
            'tax_preference',
            'exemption_reason',
            'currency',
            'payment_terms', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'gst_number', 'opening_balance', 'is_vendor',
            'shipping_address_line_1', 'shipping_address_line_2', 'shipping_city', 
            'shipping_state', 'shipping_postal_code', 'shipping_country',
        ]
        widgets = {
            # 'customer_type': forms.Select(),
            # 'country': forms.Select(attrs={'class':'form-control select2','data-placeholder':'Select country','style':'width:100%'}),
            # 'is_active': forms.CheckboxInput(),
            # 'is_vendor': forms.CheckboxInput(),
            'customer_code': forms.TextInput(attrs={'class': 'form-control','readonly': 'readonly'}),
            'customer_type': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            # 'city': forms.TextInput(attrs={'class': 'form-control'}),
            # 'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            # 'country': forms.Select(attrs={'class':'form-control select2','data-placeholder':'Select country','style':'width:100%'}),
            'country': forms.Select(attrs={'class': 'form-control select2'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_vendor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_preference': forms.Select(attrs={'class': 'form-control'}),
            'exemption_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # currency widget is configured on the field itself
            # Shipping Address
            'shipping_address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            # 'shipping_city': forms.TextInput(attrs={'class': 'form-control'}),
            # 'shipping_state': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_country': forms.Select(attrs={'class': 'form-control select2'}),
        }
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Make gst_number not required by default (will be handled dynamically)
        self.fields['gst_number'].required = False
        # Make customer type fields not required by default (will be handled in clean method)
        self.fields['first_name'].required = False
        self.fields['company_name'].required = False
        # Make shipping address fields not required
        self.fields['shipping_address_line_1'].required = False
        self.fields['shipping_city'].required = False
        self.fields['shipping_state'].required = False
        self.fields['shipping_postal_code'].required = False
        self.fields['shipping_country'].required = False

        configure_location_fields(self, 'country', 'state', 'city')
        configure_location_fields(self, 'shipping_country', 'shipping_state', 'shipping_city', shipping=True)
        # Set help texts
        self.fields['gst_treatment'].help_text = 'Select the GST treatment applicable for this customer'
        self.fields['gst_number'].help_text = 'GST identification number (required for registered businesses)'
        # Configure currency field: use ModelChoiceField with company-specific queryset
        try:
            choices = [('', 'Select currency')]
            from django.db import connections
            from Lyraerp.utils.db_utils import register_database
            from Lyraerp.utils.thread_locals import get_current_db

            company_db = get_current_db()
            if not company_db or company_db == 'default':
                company_db = getattr(company, 'db_name', None) if company else None
            if company_db and company_db not in connections.databases:
                try:
                    register_database(company_db)
                except Exception:
                    company_db = None
            if company and company_db:
                cs = Currency.objects.using(company_db).filter(company_id=company.pk, is_active=True).order_by('code')
                choices += [(c.code, c.code) for c in cs]
            # If editing an existing customer, show the saved currency as a
            # non-editable readonly text input so it cannot be changed here.
            # Keep the dropdown only for create/new customer forms.
            if self.instance and getattr(self.instance, 'pk', None):
                raw_val = getattr(self.instance, 'currency', '') or ''
                display_code = ''
                # If stored value looks like a numeric PK, try resolving to code
                try:
                    if str(raw_val).isdigit():
                        cur_obj = Currency.objects.using(company_db).filter(pk=int(raw_val)).first() if company_db else Currency.objects.filter(pk=int(raw_val)).first()
                        if cur_obj:
                            display_code = cur_obj.code
                    else:
                        # Try match by code (case-insensitive)
                        cur_obj = Currency.objects.using(company_db).filter(code__iexact=str(raw_val)).first() if company_db else Currency.objects.filter(code__iexact=str(raw_val)).first()
                        if cur_obj:
                            display_code = cur_obj.code
                        else:
                            display_code = str(raw_val)
                except Exception:
                    display_code = str(raw_val)

                self.fields['currency'] = forms.CharField(
                    required=False,
                    initial=(display_code or '').strip().upper(),
                    widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
                )
            else:
                self.fields['currency'] = forms.ChoiceField(
                    choices=choices,
                    required=False,
                    widget=forms.Select(attrs={'class': 'form-control select2'})
                )
            if getattr(self, 'instance', None) and self.instance.pk and getattr(self.instance, 'currency', None):
                # ensure initial is a code (uppercase)
                try:
                    ic = (self.instance.currency or '').strip()
                    if ic.isdigit():
                        cobj = Currency.objects.using(company_db).filter(pk=int(ic)).first() if company_db else Currency.objects.filter(pk=int(ic)).first()
                        self.initial['currency'] = (cobj.code if cobj else ic).strip().upper()
                    else:
                        self.initial['currency'] = ic.strip().upper()
                except Exception:
                    self.initial['currency'] = (self.instance.currency or '').strip().upper()

            # Only append the "new currency" sentinel when the field supports choices
            from django.forms import ChoiceField
            if isinstance(self.fields.get('currency'), ChoiceField):
                _append_new_currency_choice(self.fields['currency'])
        except Exception:
            pass

    def clean_currency(self):
        currency = (self.cleaned_data.get('currency') or '').strip().upper()
        if currency == NEW_CURRENCY_VALUE:
            raise forms.ValidationError('Please add the new currency first.')
        return currency
        
    def clean(self):
        cleaned_data = super().clean()
        gst_treatment = cleaned_data.get('gst_treatment')
        gst_number = cleaned_data.get('gst_number')
        customer_type = cleaned_data.get('customer_type')
        first_name = cleaned_data.get('first_name')
        company_name = cleaned_data.get('company_name')
        
        # Validate customer type fields
        if customer_type == 'individual':
            if not first_name or not first_name.strip():
                self.add_error('first_name', 'First name is required for individual customers.')
        elif customer_type == 'company':
            if not company_name or not company_name.strip():
                self.add_error('company_name', 'Company name is required for company customers.')
        
        # GST treatments that require GSTIN/UIN
        treatments_requiring_gstin = [
            'Registered Business - Regular',
            'Registered Business - Composition',
            'Special Economic Zone',
            'Deemed Export',
            'SEZ Developer',
            'Tax Deductor',
            'Input Service Distributor'
        ]
        
        # If GST treatment requires GSTIN and it's not provided, raise error
        if gst_treatment and gst_treatment.name in treatments_requiring_gstin:
            if not gst_number or not gst_number.strip():
                self.add_error('gst_number', 'GSTIN/UIN is required for this GST treatment.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        try:
            # Safely extract currency code from the select value.
            cur = self.cleaned_data.get('currency')
            if cur:
                # If it's a model instance, get its code; otherwise treat as string
                instance.currency = getattr(cur, 'code', str(cur))
            else:
                instance.currency = ''
        except Exception as e:
            print("currency save err", e)

        if commit:
            instance.save()
        return instance
