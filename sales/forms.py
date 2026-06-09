from django import forms
from decimal import Decimal
from .models import SalesQuotation, SalesQuotationItem, SalesPerson,SalesOrder,SalesOrderItem,SalesInvoice,SalesInvoiceItem,SalesDeliveryNote, SalesReturn, SalesReturnItem,PerformaInvoice,PerformaInvoiceItem,EWayBill,EWayBillCredential
from Tax.models import TaxGroup,Tax
from customer.models import Customer
from Items.models import Item,Uom_name,Uom
from django.utils.html import format_html
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from django_select2.forms import Select2Widget 
from warehouse.models import Warehouse
from currencies.models import Currency
from location_utils import configure_location_fields


NEW_CURRENCY_VALUE = "__new_currency__"
NEW_CURRENCY_LABEL = "+ New Currency"


def _append_new_currency_choice(field):
    choices = list(field.choices)
    if not any(str(choice[0]) == NEW_CURRENCY_VALUE for choice in choices):
        choices.append((NEW_CURRENCY_VALUE, NEW_CURRENCY_LABEL))
        field.choices = choices


DISCOUNT_TYPE_CHOICES = [
    ('flat', '₹'),
    ('percent', '%'),
    
]


def _build_tax_choices():
    choices = []
    for tg in TaxGroup.objects.prefetch_related('taxes').all():
        label = f"{tg.group_name}"
        choices.append((f"group:{tg.id}", label))

    for tax_obj in Tax.objects.filter(status=True):
        display_name = (tax_obj.display_name or tax_obj.taxname or '').strip()
        choices.append((f"tax:{tax_obj.id}", display_name))
    return choices

# class TaxSelectWidget(Select2Widget):
#     def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
#         # Generate default option dict
#         option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        
#         # Get actual value (handles ModelChoiceIteratorValue)
#         actual_value = getattr(value, 'value', value)
        
#         if actual_value:
#             try:
#                 tax_group = TaxGroup.objects.get(pk=actual_value)
#                 # Collect all tax rates in the group as comma-separated
#                 if tax_group.taxes.exists():
#                     rates = ','.join([str(t.rate) for t in tax_group.taxes.all()])
#                     option['attrs']['data-rate'] = rates
#             except TaxGroup.DoesNotExist:
#                 pass
        
#         return option


def _parse_tax_choice_value(value):
    if not value:
        return None, None
    if isinstance(value, str):
        if value.startswith('group:'):
            return 'group', value.split(':', 1)[1]
        if value.startswith('tax:'):
            return 'tax', value.split(':', 1)[1]
    return None, value


class TaxSelectWidget(Select2Widget):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        # Generate default option dict
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        
        # Get actual value (handles ModelChoiceIteratorValue)
        actual_value = getattr(value, 'value', value)
        choice_type, choice_id = _parse_tax_choice_value(actual_value)

        if choice_type == 'group' and choice_id:
            try:
                tax_group = TaxGroup.objects.prefetch_related('taxes').get(pk=choice_id)
                if tax_group.taxes.exists():
                    total_rate = sum(t.rate for t in tax_group.taxes.all())
                    option['attrs']['data-rate'] = str(total_rate)
            except TaxGroup.DoesNotExist:
                pass
        elif choice_type == 'tax' and choice_id:
            try:
                tax_obj = Tax.objects.get(pk=choice_id)
                option['attrs']['data-rate'] = str(tax_obj.rate or 0)
            except Tax.DoesNotExist:
                pass
        
        return option



class SalesQuotationForm(forms.ModelForm):
    class Meta:
        model = SalesQuotation
        fields = '__all__'
        widgets = {
            # 'customer': forms.Select(attrs={'class': 'form-control vendor-select'}),
            'customer': forms.Select(attrs={'class': 'form-control customer-select', 'id': 'customer_select'}),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'autocomplete': 'off',
                'inputmode': 'numeric',
                'placeholder': 'YYYY-MM-DD'
            }),
            'sales_person': forms.Select(attrs={'class': 'form-control sales_person-select', 'id': 'sales_person_select'}),
            'place_of_supply': forms.TextInput(attrs={'class': 'form-control', 'id': 'place-of-supply', 'type': 'hidden'}),
            'document_currency': forms.Select(attrs={'class': 'form-control select2', 'id': 'document_currency'}),
            'fx_rate_to_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '1.000000'}),
            'fx_rate_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'autocomplete': 'off',
                'inputmode': 'numeric',
                'placeholder': 'YYYY-MM-DD'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Populate currency choices from company currencies
        try:
            if company:
                self.fields['document_currency'].queryset = Currency.objects.filter(company=company, is_active=True).order_by('code')
            else:
                self.fields['document_currency'].queryset = Currency.objects.filter(is_active=True).order_by('code')
        except Exception:
            self.fields['document_currency'].queryset = Currency.objects.none()

class SalesQuotationItemForm(forms.ModelForm):
    # product = forms.ModelChoiceField(queryset=Item.objects.all())
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(max_digits=18, decimal_places=6, widget=forms.HiddenInput(), required=False)
    # prd_tax = forms.ModelChoiceField(
    #         queryset=TaxGroup.objects.all(),
    #         widget=TaxSelectWidget(attrs={'class': 'tax-select'})
    #     )
    # prd_tax = forms.ChoiceField(
    #     choices=[],
    #     widget=forms.Select(attrs={'class': 'tax-select'})
    # )
    prd_tax = forms.ChoiceField(widget=TaxSelectWidget(attrs={'class': 'tax-select'}),required=False)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 1, 'cols': 20, 'style': 'resize:none;font-size:12px;'})  # Smaller textarea
    )

    class Meta:
        model = SalesQuotationItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price','prd_tax','description']
        

        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select','data-allow-clear': 'true',}),
            'quantity': forms.NumberInput(attrs={'class': 'qty', 'min': '0.01', 'step': '0.01'}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount','value': 0}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),  # if you need discount-type class
            # 'prd_tax': Select2Widget(attrs={'class': 'tax-select'}),
            
            'price': forms.NumberInput(attrs={'class': 'price', 'min': '0.01', 'step': '0.01'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial/default values here
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        # Allow blank rows (e.g. when a user has an extra empty line)
        # so the formset validation doesn't fail before we decide to save lines.
        self.fields['product'].required = False
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
        # Always ensure hidden fields have valid initial values
        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        if (o_price in (None, '', Decimal('0.00'), 0) and
                getattr(self.instance, 'pk', None) and
                getattr(self.instance, 'Sales_quotation', None)):
            fx_rate = getattr(self.instance.Sales_quotation, 'fx_rate_to_base', None) or Decimal('1')
            o_price = (Decimal(str(getattr(self.instance, 'price', 0) or 0)) * Decimal(str(fx_rate))).quantize(Decimal('0.000001'))
        self.fields['o_price'].initial = o_price if o_price is not None else 0
        # self.fields['prd_tax'].queryset = TaxGroup.objects.all()
        # self.fields['prd_tax'].label_from_instance = lambda obj: obj.group_name

        # ---------------- TAX PREFILL ----------------
        tax_choices = _build_tax_choices()
        self.fields['prd_tax'].choices = [('', 'Select Tax Group')] + tax_choices
        if self.instance and self.instance.pk:
            saved_taxgroup = self.instance.prd_taxgroup  # e.g. "GST 18"
            if saved_taxgroup:
                tax_obj = TaxGroup.objects.filter(group_name__iexact=saved_taxgroup).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"group:{tax_obj.id}"
            elif self.instance.prd_tax:
                tax_obj = Tax.objects.filter(rate=self.instance.prd_tax).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"tax:{tax_obj.id}"
        # ---------------- PRODUCT + UOM PREFILL ----------------
        # ✅ Add dynamic label_from_instance for product field
        def product_label(instance):
            uom_obj = (
                Uom.objects
                .filter(item=instance)
                .select_related('name')
                .first()
            )
            uom_name = uom_obj.name.name if (uom_obj and uom_obj.name) else ''
            return format_html(f"{instance.name} ({uom_name})") if uom_name else instance.name

        self.fields['product'].queryset = Item.objects.all()
        self.fields['product'].label_from_instance = product_label
        # self.fields['prd_distype'].initial = 'percent'  # or 'flat'
        # Similarly for others if needed

    def clean_prd_tax(self):
        """
        `prd_tax` is a DecimalField in the model, but the UI sends a token like
        `group:<id>` or `tax:<id>`. Convert the token into an actual decimal rate
        so ModelForm validation doesn't fail with:
        "value must be a decimal number."
        """
        selection = (self.cleaned_data.get('prd_tax') or '').strip()
        if not selection:
            return None

        try:
            if selection.startswith('group:'):
                tax_group_id = selection.split(':', 1)[1]
                tax_group = TaxGroup.objects.prefetch_related('taxes').filter(id=tax_group_id).first()
                if not tax_group:
                    return None
                total_rate = Decimal(sum(t.rate for t in tax_group.taxes.all()))
                return total_rate.quantize(Decimal('0.01'))

            if selection.startswith('tax:'):
                tax_id = selection.split(':', 1)[1]
                tax_obj = Tax.objects.filter(id=tax_id).select_related('taxtype').first()
                if not tax_obj:
                    return None
                rate = Decimal(str(tax_obj.rate or 0))
                return rate.quantize(Decimal('0.01'))

            # Fallback: attempt to parse numeric rate
            rate = Decimal(str(selection))
            return rate.quantize(Decimal('0.01'))
        except Exception:
            return None

# class CustomerForm(forms.ModelForm):
#     class Meta:
#         model = Customer
#         exclude = ['created_by', 'updated_by']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ['created_by', 'updated_by','opening_balance','postal_code','is_active']
        widgets = {
            'country': CountrySelectWidget(attrs={'class': 'form-control select2'}),
        }
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if all(field in self.fields for field in ('country', 'state', 'city')):
            configure_location_fields(self, 'country', 'state', 'city')
        if all(field in self.fields for field in ('shipping_country', 'shipping_state', 'shipping_city')):
            configure_location_fields(self, 'shipping_country', 'shipping_state', 'shipping_city', shipping=True)


        # Populate currency choices from company currencies
        try:
            choices = [('', 'Select currency')]
            if company:
                cs = Currency.objects.filter(company=company, is_active=True).order_by('code')
                choices += [(c.code, c.code) for c in cs]
            self.fields['currency'] = forms.ChoiceField(choices=choices, required=False, widget=forms.Select(attrs={'class': 'form-control select2'}))
            if getattr(self, 'instance', None) and self.instance.pk and getattr(self.instance, 'currency', None):
                self.initial['currency'] = (self.instance.currency or '').strip().upper()
            _append_new_currency_choice(self.fields['currency'])
        except Exception:
            pass

        customer_type = self.data.get('customer_type') or (self.instance.customer_type if self.instance.pk else None)
        # self.fields['phone'].required = True
        # Make fields conditionally required based on customer_type
        if customer_type == 'individual':
            self.fields['first_name'].required = True
            # self.fields['last_name'].required = True
            self.fields['company_name'].required = False
        elif customer_type == 'company':
            self.fields['company_name'].required = True
            self.fields['first_name'].required = False
            # self.fields['last_name'].required = False
    #  VALIDATION LEVEL CONTROL added on 2024-06-20 by neha(double protection along with save method)
    def clean(self):
        cleaned_data = super().clean()
        customer_type = cleaned_data.get('customer_type')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        company_name = cleaned_data.get('company_name')

        if customer_type == 'individual':
            if not first_name:
                self.add_error('first_name', 'First name is required for individual customer.')
            
            # Remove company_name from cleaned data
            cleaned_data['company_name'] = ''

        elif customer_type == 'company':
            if not company_name:
                self.add_error('company_name', 'Company name is required for company customer.')
            
            # Remove individual fields
            cleaned_data['first_name'] = ''
            cleaned_data['last_name'] = ''

        return cleaned_data


    # SAVE LEVEL SAFETY (DOUBLE PROTECTION)
    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.customer_type == 'individual':
            instance.company_name = ''
        elif instance.customer_type == 'company':
            instance.first_name = ''
            instance.last_name = ''

        if commit:
            instance.save()

        return instance

class SalesPersonForm(forms.ModelForm):
    class Meta:
        model = SalesPerson
        fields = '__all__'
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'tel',
                'pattern': '[0-9]+',  # allows multiple digits
                'title': 'Please enter digits only',
            }),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()

        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")

        return phone



class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = '__all__'
        widgets = {
            # 'customer': forms.Select(attrs={'class': 'form-control vendor-select'}),
            'customer': forms.Select(attrs={'class': 'form-control customer-select', 'id': 'customer_select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sales_person': forms.Select(attrs={'class': 'form-control sales_person-select', 'id': 'sales_person_select'}),
        }

class SalesOrderItemForm(forms.ModelForm):
    # product = forms.ModelChoiceField(queryset=Item.objects.all())
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(max_digits=18, decimal_places=6, widget=forms.HiddenInput(), required=False)
    # prd_tax = forms.ModelChoiceField(
    #         queryset=TaxGroup.objects.all(),
    #         widget=TaxSelectWidget(attrs={'class': 'tax-select'})
    #     )
    # prd_tax = forms.ChoiceField(
    #     choices=[],
    #     widget=forms.Select(attrs={'class': 'tax-select'})
    # )
    prd_tax = forms.ChoiceField(widget=TaxSelectWidget(attrs={'class': 'tax-select'}),required=False)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 1, 'cols': 20, 'style': 'resize:none;font-size:12px;'})  # Smaller textarea
    )

    class Meta:
        model = SalesOrderItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price','prd_tax','description']
        

        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select','data-allow-clear': 'true',}),
            'quantity': forms.NumberInput(attrs={'class': 'qty'}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount','value': 0}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),  # if you need discount-type class
            # 'prd_tax': Select2Widget(attrs={'class': 'tax-select'}),
            
            'price': forms.NumberInput(attrs={'class': 'price', 'min': '0.01', 'step': '0.01'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial/default values here
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
        # Always ensure hidden fields have valid initial values
        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        if (o_price in (None, '', Decimal('0.00'), 0) and
                getattr(self.instance, 'pk', None) and
                getattr(self.instance, 'sales_order', None)):
            fx_rate = getattr(self.instance.sales_order, 'fx_rate_to_base', None) or Decimal('1')
            o_price = (Decimal(str(getattr(self.instance, 'price', 0) or 0)) * Decimal(str(fx_rate))).quantize(Decimal('0.000001'))
        self.fields['o_price'].initial = o_price if o_price is not None else 0
        # self.fields['prd_tax'].queryset = TaxGroup.objects.all()
        # self.fields['prd_tax'].label_from_instance = lambda obj: obj.group_name

        # ---------------- TAX PREFILL ----------------
        tax_choices = _build_tax_choices()
        self.fields['prd_tax'].choices = [('', 'Select Tax Group')] + tax_choices
        if self.instance and self.instance.pk:
            saved_taxgroup = self.instance.prd_taxgroup  # e.g. "GST 18"
            if saved_taxgroup:
                tax_obj = TaxGroup.objects.filter(group_name__iexact=saved_taxgroup).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"group:{tax_obj.id}"
            elif self.instance.prd_tax:
                tax_obj = Tax.objects.filter(rate=self.instance.prd_tax).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"tax:{tax_obj.id}"
        # ---------------- PRODUCT + UOM PREFILL ----------------
        # ✅ Add dynamic label_from_instance for product field
        def product_label(instance):
            uom_obj = (
                Uom.objects
                .filter(item=instance)
                .select_related('name')
                .first()
            )
            uom_name = uom_obj.name.name if (uom_obj and uom_obj.name) else ''
            return format_html(f"{instance.name} ({uom_name})") if uom_name else instance.name

        self.fields['product'].queryset = Item.objects.all()
        self.fields['product'].label_from_instance = product_label

    def clean_prd_tax(self):
        """
        `prd_tax` is a DecimalField in the model, but the UI sends a token like
        `group:<id>` or `tax:<id>`. Convert the token into an actual decimal rate
        so ModelForm validation doesn't fail with:
        "value must be a decimal number."
        """
        selection = (self.cleaned_data.get('prd_tax') or '').strip()
        if not selection:
            return None

        try:
            if selection.startswith('group:'):
                tax_group_id = selection.split(':', 1)[1]
                tax_group = TaxGroup.objects.prefetch_related('taxes').filter(id=tax_group_id).first()
                if not tax_group:
                    return None
                total_rate = Decimal(sum(t.rate for t in tax_group.taxes.all()))
                return total_rate.quantize(Decimal('0.01'))

            if selection.startswith('tax:'):
                tax_id = selection.split(':', 1)[1]
                tax_obj = Tax.objects.filter(id=tax_id).select_related('taxtype').first()
                if not tax_obj:
                    return None
                rate = Decimal(str(tax_obj.rate or 0))
                return rate.quantize(Decimal('0.01'))

            # Fallback: attempt to parse numeric rate
            rate = Decimal(str(selection))
            return rate.quantize(Decimal('0.01'))
        except Exception:
            return None


class SalesInvoiceForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=Select2Widget(attrs={'class': 'form-control', 'id': 'customer_select', 'data-minimum-input-length': '1'}),
        required=True
    )
    sales_person = forms.ModelChoiceField(
        queryset=SalesPerson.objects.all(),
        widget=Select2Widget(attrs={'class': 'form-control', 'id': 'sales_person_select', 'data-minimum-input-length': '1'}),
        required=False
    )
    
    class Meta:
        model = SalesInvoice
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class SalesInvoiceItemForm(forms.ModelForm):
    # product = forms.ModelChoiceField(queryset=Item.objects.all())
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(max_digits=18, decimal_places=6, widget=forms.HiddenInput(), required=False)
    # prd_tax = forms.ModelChoiceField(
    #         queryset=TaxGroup.objects.all(),
    #         widget=TaxSelectWidget(attrs={'class': 'tax-select'})
    #     )
    # prd_tax = forms.ChoiceField(
    #     choices=[],
    #     widget=forms.Select(attrs={'class': 'tax-select'})
    # )
    prd_tax = forms.ChoiceField(widget=TaxSelectWidget(attrs={'class': 'tax-select'}),required=False)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 1, 'cols': 20, 'style': 'resize:none;font-size:12px;'})  # Smaller textarea
    )

    class Meta:
        model = SalesInvoiceItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price','prd_tax','description']
        

        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select','data-allow-clear': 'true',}),
            'quantity': forms.NumberInput(attrs={'class': 'qty'}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount','value': 0}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),  # if you need discount-type class
            # 'prd_tax': Select2Widget(attrs={'class': 'tax-select'}),
            
            'price': forms.NumberInput(attrs={'class': 'price', 'min': '0.01', 'step': '0.01'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial/default values here
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
        # Always ensure hidden fields have valid initial values
        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        if (o_price in (None, '', Decimal('0.00'), 0) and
                getattr(self.instance, 'pk', None) and
                getattr(self.instance, 'sales_inv', None)):
            fx_rate = getattr(self.instance.sales_inv, 'fx_rate_to_base', None) or Decimal('1')
            o_price = (Decimal(str(getattr(self.instance, 'price', 0) or 0)) * Decimal(str(fx_rate))).quantize(Decimal('0.000001'))
        self.fields['o_price'].initial = o_price if o_price is not None else 0
        # self.fields['prd_tax'].queryset = TaxGroup.objects.all()
        # self.fields['prd_tax'].label_from_instance = lambda obj: obj.group_name

        # ---------------- TAX PREFILL ----------------
        tax_choices = _build_tax_choices()
        self.fields['prd_tax'].choices = [('', 'Select Tax Group')] + tax_choices
        if self.instance and self.instance.pk:
            saved_taxgroup = self.instance.prd_taxgroup  # e.g. "GST 18"
            if saved_taxgroup:
                tax_obj = TaxGroup.objects.filter(group_name__iexact=saved_taxgroup).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"group:{tax_obj.id}"
            elif self.instance.prd_tax:
                tax_obj = Tax.objects.filter(rate=self.instance.prd_tax).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"tax:{tax_obj.id}"
        # ---------------- PRODUCT + UOM PREFILL ----------------
        # ✅ Add dynamic label_from_instance for product field
        def product_label(instance):
            uom_obj = (
                Uom.objects
                .filter(item=instance)
                .select_related('name')
                .first()
            )
            uom_name = uom_obj.name.name if (uom_obj and uom_obj.name) else ''
            return format_html(f"{instance.name} ({uom_name})") if uom_name else instance.name

        self.fields['product'].queryset = Item.objects.all()
        self.fields['product'].label_from_instance = product_label

    def clean_prd_tax(self):
        """
        `prd_tax` is a DecimalField in the model, but the UI sends a token like
        `group:<id>` or `tax:<id>`. Convert the token into an actual decimal rate
        so ModelForm validation doesn't fail with:
        "value must be a decimal number."
        """
        selection = (self.cleaned_data.get('prd_tax') or '').strip()
        if not selection:
            return None

        try:
            if selection.startswith('group:'):
                tax_group_id = selection.split(':', 1)[1]
                tax_group = TaxGroup.objects.prefetch_related('taxes').filter(id=tax_group_id).first()
                if not tax_group:
                    return None
                total_rate = Decimal(sum(t.rate for t in tax_group.taxes.all()))
                return total_rate.quantize(Decimal('0.01'))

            if selection.startswith('tax:'):
                tax_id = selection.split(':', 1)[1]
                tax_obj = Tax.objects.filter(id=tax_id).select_related('taxtype').first()
                if not tax_obj:
                    return None
                rate = Decimal(str(tax_obj.rate or 0))
                return rate.quantize(Decimal('0.01'))

            # Fallback: attempt to parse numeric rate
            rate = Decimal(str(selection))
            return rate.quantize(Decimal('0.01'))
        except Exception:
            return None


class SalesDeliveryNoteForm(forms.ModelForm):
    class Meta:
        model = SalesDeliveryNote
        fields = ['sales_invoice', 'warehouse', 'delivery_date', 'status', 
                  'shipped_by', 'courier_name', 'tracking_number', 'notes']
        widgets = {
            'sales_invoice': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'delivery_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'shipped_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of shipper'
            }),
            'courier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FedEx, UPS, DHL'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tracking number'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about this delivery...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter invoices to show only confirmed/shipped ones
        self.fields['sales_invoice'].queryset = SalesInvoice.objects.filter(
            status='Open'
        ).select_related('customer')
        
        # All active warehouses
        self.fields['warehouse'].queryset = Warehouse.objects.filter(status=True)


class SalesReturnForm(forms.ModelForm):
    class Meta:
        model = SalesReturn
        fields = ['sales_invoice', 'warehouse', 'date', 'status', 
                  'shipped_by', 'courier_name', 'tracking_number', 'notes']
        widgets = {
            'sales_invoice': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'shipped_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of shipper'
            }),
            'courier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FedEx, UPS, DHL'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tracking number'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about this return...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For new returns, show invoices with Closed status
        # For existing returns, include the current invoice in queryset
        queryset = SalesInvoice.objects.filter(status='Closed').select_related('customer')
        
        # If editing an existing return, ensure the current invoice is included
        if self.instance and self.instance.pk:
            # Create a union of the filtered queryset and the current invoice
            from django.db.models import Q
            queryset = SalesInvoice.objects.filter(
                Q(status='Closed') | Q(pk=self.instance.sales_invoice_id)
            ).select_related('customer').distinct()
        
        self.fields['sales_invoice'].queryset = queryset
        
        # All active warehouses
        self.fields['warehouse'].queryset = Warehouse.objects.filter(status=True)



class PerformaInvoiceForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=Select2Widget(attrs={'class': 'form-control', 'id': 'customer_select', 'data-minimum-input-length': '1'}),
        required=True
    )
    sales_person = forms.ModelChoiceField(
        queryset=SalesPerson.objects.all(),
        widget=Select2Widget(attrs={'class': 'form-control', 'id': 'sales_person_select', 'data-minimum-input-length': '1'}),
        required=False
    )
    
    class Meta:
        model = PerformaInvoice
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


class PerformaInvoiceItemForm(forms.ModelForm):
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(max_digits=18, decimal_places=6, widget=forms.HiddenInput(), required=False)
    prd_tax = forms.ChoiceField(widget=TaxSelectWidget(attrs={'class': 'tax-select'}), required=False)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 1, 'cols': 20, 'style': 'resize:none;font-size:12px;'})
    )

    class Meta:
        model = PerformaInvoiceItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price', 'prd_tax', 'description']
        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select', 'data-allow-clear': 'true'}),
            'quantity': forms.NumberInput(attrs={'class': 'qty'}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount', 'value': 0}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),
            'price': forms.NumberInput(attrs={'class': 'price', 'min': '0.01', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
            self.fields['o_price'].initial = getattr(self.instance, 'o_price', None)

        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        self.fields['o_price'].initial = o_price if o_price is not None else 0

        # ---------------- TAX PREFILL ----------------
        tax_choices = _build_tax_choices()
        self.fields['prd_tax'].choices = [('', 'Select Tax Group')] + tax_choices

        if self.instance and self.instance.pk:
            saved_taxgroup = self.instance.prd_taxgroup
            if saved_taxgroup:
                tax_obj = TaxGroup.objects.filter(group_name__iexact=saved_taxgroup).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"group:{tax_obj.id}"
            elif self.instance.prd_tax:
                tax_obj = Tax.objects.filter(rate=self.instance.prd_tax).first()
                if tax_obj:
                    self.initial['prd_tax'] = f"tax:{tax_obj.id}"

        def product_label(instance):
            uom_obj = (
                Uom.objects
                .filter(item=instance)
                .select_related('name')
                .first()
            )
            uom_name = uom_obj.name.name if (uom_obj and uom_obj.name) else ''
            return format_html(f"{instance.name} ({uom_name})") if uom_name else instance.name

        self.fields['product'].queryset = Item.objects.all()
        self.fields['product'].label_from_instance = product_label

    def clean_prd_tax(self):
        """
        `prd_tax` is a DecimalField in the model, but the UI sends a token like
        `group:<id>` or `tax:<id>`. Convert the token into an actual decimal rate
        so ModelForm validation doesn't fail with:
        "value must be a decimal number."
        """
        selection = (self.cleaned_data.get('prd_tax') or '').strip()
        if not selection:
            return None

        try:
            if selection.startswith('group:'):
                tax_group_id = selection.split(':', 1)[1]
                tax_group = TaxGroup.objects.prefetch_related('taxes').filter(id=tax_group_id).first()
                if not tax_group:
                    return None
                total_rate = Decimal(sum(t.rate for t in tax_group.taxes.all()))
                return total_rate.quantize(Decimal('0.01'))

            if selection.startswith('tax:'):
                tax_id = selection.split(':', 1)[1]
                tax_obj = Tax.objects.filter(id=tax_id).select_related('taxtype').first()
                if not tax_obj:
                    return None
                rate = Decimal(str(tax_obj.rate or 0))
                return rate.quantize(Decimal('0.01'))

            # Fallback: attempt to parse numeric rate
            rate = Decimal(str(selection))
            return rate.quantize(Decimal('0.01'))
        except Exception:
            return None


class EWayBillForm(forms.ModelForm):
    class Meta:
        model = EWayBill
        fields = [
            'mode_of_transport',
            'vehicle_number',
            'vehicle_type',
            'transporter_id',
            'transporter_name',
            'transport_doc_no',
            'transport_doc_date',
            'approximate_distance',
            'gstin_to',
            'place_to',
            'pincode_to',
            'state_to',
        ]
        widgets = {
            'transport_doc_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'mode_of_transport': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'vehicle_type': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'vehicle_number': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g. KA01AB1234'}
            ),
            'transporter_id': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Transporter GSTIN (optional)'}
            ),
            'transporter_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'transport_doc_no': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'approximate_distance': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '0'}
            ),
            'gstin_to': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': '15', 'placeholder': 'Recipient GSTIN'}
            ),
            'place_to': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Destination city'}
            ),
            'pincode_to': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': '6', 'placeholder': '6-digit pincode'}
            ),
            'state_to': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Destination state'}
            ),
        }


class EWayBillCredentialForm(forms.ModelForm):
    """Form for entering NIC E-Way Bill API credentials."""

    password_raw = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter NIC portal password (leave blank to keep existing)",
                "autocomplete": "new-password",
            }
        ),
        required=False,
        help_text="Leave blank to keep the existing password.",
    )

    class Meta:
        model = EWayBillCredential
        fields = [
            "gstin",
            "username",
            "app_key",
            "nic_public_key",
            "is_sandbox",
            "is_active",
        ]
        widgets = {
            "gstin": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 29AAAAA0000A1Z5",
                "maxlength": "15",
            }),
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "username",
            }),
            "app_key": forms.TextInput(attrs={
                "class": "form-control font-monospace",
                "readonly": "readonly",
            }),
            "nic_public_key": forms.Textarea(attrs={
                "class": "form-control font-monospace",
                "rows": 8,
                "placeholder": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
            }),
            "is_sandbox": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "gstin": "GSTIN",
            "username": "NIC Portal Username",
            "app_key": "App Key (auto-generated)",
            "nic_public_key": "NIC Public Key (PEM)",
            "is_sandbox": "Use Sandbox / Testing Mode",
            "is_active": "Active",
        }

    def __init__(self, *args, mock_mode=False, **kwargs):
        """In mock mode, make credential fields optional."""
        super().__init__(*args, **kwargs)
        self.mock_mode = mock_mode
        
        # app_key is read-only and auto-generated, so don't require it
        self.fields['app_key'].required = False
        
        if mock_mode:
            # Mock mode: don't require credentials
            self.fields['gstin'].required = False
            self.fields['username'].required = False
            self.fields['nic_public_key'].required = False

