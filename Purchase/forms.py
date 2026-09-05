from django import forms
from django.utils.html import format_html
from .models import PurchaseOrder, Vendor,PurchaseOrder,PurchaseOrderItem,Bill,BillItem,BillPayment,DeliveryNote,DeliveryNoteItem,PurchaseReturn,PurchaseReturnItem
from django.forms import inlineformset_factory
from .models import Vendor, ContactPerson
from django_select2.forms import Select2Widget 
from Tax.models import TaxGroup,Tax
from Items.models import Item,Uom_name,Uom
from customer.models import GstTreatment
from PayTerms.models import PayTerms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django.db.models import Q
from decimal import Decimal
from currencies.models import Currency
from location_utils import configure_location_fields

from warehouse.models import Warehouse

NEW_CURRENCY_VALUE = "__new_currency__"
NEW_CURRENCY_LABEL = "+ New Currency"


def _append_new_currency_choice(field):
    # Shared JS turns this sentinel into a "create currency" flow.
    choices = list(field.choices)
    if not any(str(choice[0]) == NEW_CURRENCY_VALUE for choice in choices):
        choices.append((NEW_CURRENCY_VALUE, NEW_CURRENCY_LABEL))
        field.choices = choices

def _resolve_company_context(company=None):
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

    if company and company_db and company_db != 'default':
        company_db_name = getattr(company, 'db_name', None)
        if company_db_name and company_db_name != company_db:
            try:
                company_from_db = Company.objects.using(company_db).filter(pk=company.pk).first()
                if company_from_db is None:
                    company_from_db = Company.objects.using(company_db).order_by('id').first()
                if company_from_db:
                    company = company_from_db
            except Exception:
                pass

    if company is None and company_db:
        try:
            company = Company.objects.using(company_db).order_by('id').first()
        except Exception:
            company = None

    if company is None:
        try:
            company = Company.objects.using('default').order_by('id').first()
            if company and not company_db:
                company_db = getattr(company, 'db_name', None) or 'default'
        except Exception:
            company = None

    return company, company_db

def build_tax_group_choices():
    tax_choices = [('', 'Select Tax'), ('non_taxable', 'Non-taxable')]
    for tg in TaxGroup.objects.prefetch_related('taxes').all():
        label = f"{tg.group_name}"
        tax_choices.append((f"group:{tg.id}", label))
    for tax in Tax.objects.select_related('taxtype').all():
        label = getattr(tax, 'display_name', None) or tax.taxname
        tax_choices.append((f"tax:{tax.id}", label))
    return tax_choices


def get_saved_tax_group_id(instance):
    if not instance or not instance.pk:
        return None

    saved_taxgroup = (instance.prd_taxgroup or '').strip()
    if saved_taxgroup:
        tax_group = TaxGroup.objects.filter(group_name__iexact=saved_taxgroup).first()
        if tax_group:
            return f"group:{tax_group.id}"

        tax_obj = Tax.objects.filter(name__iexact=saved_taxgroup).first()
        if not tax_obj:
            tax_obj = Tax.objects.filter(taxname__iexact=saved_taxgroup).first()
        if not tax_obj:
            tax_obj = Tax.objects.filter(
                Q(name__iexact=saved_taxgroup) | Q(taxname__iexact=saved_taxgroup)
            ).first()
        if tax_obj:
            return f"tax:{tax_obj.id}"

    saved_rate = getattr(instance, 'prd_tax', None)
    if saved_rate in (None, ''):
        return None

    try:
        if Decimal(saved_rate) == Decimal('0'):
            return 'non_taxable'
    except Exception:
        pass

    for tax_group in TaxGroup.objects.prefetch_related('taxes').all():
        total_rate = sum((t.rate or 0) for t in tax_group.taxes.all())
        if total_rate == saved_rate:
            return f"group:{tax_group.id}"

    tax_obj = Tax.objects.filter(rate=saved_rate).first()
    if tax_obj:
        return f"tax:{tax_obj.id}"

    return None



class VendorForm(forms.ModelForm):
    
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
        model = Vendor
        fields = [
            'vendor_code', 'vendor_type', 'first_name', 'last_name', 'company_name',
            'email', 'phone', 'mobile','gst_treatment','pan_number',
            'tax_preference',
            'exemption_reason',
            'currency',
            'payment_terms', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'tax_number', 'opening_balance', 'is_customer',
            'shipping_address_line_1', 'shipping_address_line_2', 'shipping_city', 
            'shipping_state', 'shipping_postal_code', 'shipping_country',
        ]
        widgets = {
            # 'vendor_type': forms.Select(),
            # 'country': forms.Select(attrs={'class':'form-control select2','data-placeholder':'Select country','style':'width:100%'}),
            # 'is_active': forms.CheckboxInput(),
            # 'is_customer': forms.CheckboxInput(),
            'vendor_code': forms.TextInput(attrs={'class': 'form-control','readonly': 'readonly'}),
            'vendor_type': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            # 'city': forms.TextInput(attrs={'class': 'form-control'}),
            # 'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            # 'country': forms.Select(attrs={'class':'form-control select2','data-placeholder':'Select country','style':'width:100%'}),
            'country': forms.Select(attrs={'class': 'form-control select2'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_customer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_preference': forms.Select(attrs={'class': 'form-control'}),
            'exemption_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # currency widget configured on the field in __init__
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
        
        # Make tax_number not required by default (will be handled dynamically)
        self.fields['tax_number'].required = False
        # Make vendor type fields not required by default (will be handled in clean method)
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
        self.fields['gst_treatment'].help_text = 'Select the GST treatment applicable for this vendor'
        self.fields['tax_number'].help_text = 'GST identification number (required for registered businesses)'
        # Configure currency field: use ChoiceField with company-specific queryset
        try:
            company, company_db = _resolve_company_context(company)
            choices = [('', 'Select currency')]
            if company_db:
                currency_qs = Currency.objects.using(company_db).filter(is_active=True).order_by('code')
                if company:
                    currency_qs = currency_qs.filter(company_id=company.pk)
                cs = currency_qs
                choices += [(c.code, c.code) for c in cs]
            self.fields['currency'] = forms.ChoiceField(
                choices=choices,
                required=True,
                widget=forms.Select(attrs={'class': 'form-control select2'})
            )
            if getattr(self, 'instance', None) and self.instance.pk and getattr(self.instance, 'currency', None):
                self.initial['currency'] = (self.instance.currency or '').strip().upper()
            _append_new_currency_choice(self.fields['currency'])
        except Exception:
            pass

    def clean_currency(self):
        currency = (self.cleaned_data.get('currency') or '').strip().upper()
        if currency == NEW_CURRENCY_VALUE:
            raise forms.ValidationError('Please add the new currency first.')
        if not currency:
            raise forms.ValidationError('Currency is required.')
        return currency
        
    def clean(self):
        cleaned_data = super().clean()
        gst_treatment = cleaned_data.get('gst_treatment')
        tax_number = cleaned_data.get('tax_number')
        vendor_type = cleaned_data.get('vendor_type')
        first_name = cleaned_data.get('first_name')
        company_name = cleaned_data.get('company_name')
        
        # Validate vendor type fields
        if vendor_type == 'individual':
            if not first_name or not first_name.strip():
                self.add_error('first_name', 'First name is required for individual vendors.')
        elif vendor_type == 'company':
            if not company_name or not company_name.strip():
                self.add_error('company_name', 'Company name is required for company vendors.')
        
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
            if not tax_number or not tax_number.strip():
                self.add_error('tax_number', 'GSTIN/UIN is required for this GST treatment.')
        
        return cleaned_data 
        #end of vendorform clean

    def save(self, commit=True):
        instance = super().save(commit=False)
        # If currency is a Currency model instance, store its code on the Vendor.currency CharField
        try:
            cur = self.cleaned_data.get('currency')
            if cur:
                instance.currency = getattr(cur, 'code', str(cur))
            else:
                instance.currency = ''
        except Exception:
            pass
        if commit:
            instance.save()
        return instance

class VendorFormmodal(forms.ModelForm):
    class Meta:
        model = Vendor
        exclude = ['created_by', 'updated_by','opening_balance','postal_code','is_active']
        widgets = {
            'country': CountrySelectWidget(attrs={'class': 'form-control select2'}),
            'payment_terms': forms.Select(attrs={'class': 'form-control select2'}),
        }
    # vendorformmodal init 

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if all(field in self.fields for field in ('country', 'state', 'city')):
            configure_location_fields(self, 'country', 'state', 'city')
        if all(field in self.fields for field in ('shipping_country', 'shipping_state', 'shipping_city')):
            configure_location_fields(self, 'shipping_country', 'shipping_state', 'shipping_city', shipping=True)
        
        
        vendor_type = self.data.get('vendor_type') or (self.instance.vendor_type if self.instance.pk else None)
        # self.fields['phone'].required = True
        # Make fields conditionally required based on vendor_type
        if vendor_type == 'individual':
            self.fields['first_name'].required = True
            # self.fields['last_name'].required = True
            self.fields['company_name'].required = False
        elif vendor_type == 'company':
            self.fields['company_name'].required = True
            self.fields['first_name'].required = False
            # self.fields['last_name'].required = False

        #venforformmodal init continued - dynamic currency choices    
            
        # Populate currency choices for the modal and add the shared "new currency" action.
        try:
            company, company_db = _resolve_company_context(company)
            choices = [('', 'Select currency')]
            if company_db:
                currency_qs = Currency.objects.using(company_db).filter(is_active=True).order_by('code')
                if company:
                    currency_qs = currency_qs.filter(company_id=company.pk)
                cs = currency_qs
                choices += [(c.code, c.code) for c in cs]
            self.fields['currency'] = forms.ChoiceField(
                choices=choices,
                required=False,
                widget=forms.Select(attrs={'class': 'form-control select2'})
            )
            if getattr(self, 'instance', None) and self.instance.pk and getattr(self.instance, 'currency', None):
                self.initial['currency'] = (self.instance.currency or '').strip().upper()
            _append_new_currency_choice(self.fields['currency'])
        except Exception:
            pass

    def clean_currency(self):
        currency = (self.cleaned_data.get('currency') or '').strip().upper()
        if currency == NEW_CURRENCY_VALUE:
            raise forms.ValidationError('Please add the new currency first.')
        return currency

    def save(self, commit=True):
        instance = super().save(commit=False)
        try:
            cur = self.cleaned_data.get('currency')
            if cur:
                instance.currency = getattr(cur, 'code', str(cur))
            else:
                instance.currency = ''
        except Exception:
            pass
        if commit:
            instance.save()
        return instance
     #  VALIDATION LEVEL CONTROL added by neha on 20-2-26

    def clean(self):
        cleaned_data = super().clean()
        vendor_type = cleaned_data.get('vendor_type')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        company_name = cleaned_data.get('company_name')

        if vendor_type == 'individual':
            if not first_name:
                self.add_error('first_name', 'First name is required for individual vendor.')

            # Remove company_name
            cleaned_data['company_name'] = ''

        elif vendor_type == 'company':
            if not company_name:
                self.add_error('company_name', 'Company name is required for company vendor.')

            # Remove individual fields
            cleaned_data['first_name'] = ''
            cleaned_data['last_name'] = ''

        return cleaned_data


    #  SAVE LEVEL SAFETY (DOUBLE PROTECTION)
    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.vendor_type == 'individual':
            instance.company_name = ''
        elif instance.vendor_type == 'company':
            instance.first_name = ''
            instance.last_name = ''

        if commit:
            instance.save()

        return instance


class ContactPersonForm(forms.ModelForm):
    class Meta:
        model = ContactPerson
        fields = ['name', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


ContactPersonFormSet = inlineformset_factory(
    Vendor,
    ContactPerson,
    form=ContactPersonForm,
    extra=0,
    can_delete=True
)





#added by neha on 16-12-25
class TaxSelectWidget(Select2Widget):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        # Generate default option dict
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        
        # Get actual value (handles ModelChoiceIteratorValue)
        actual_value = getattr(value, 'value', value)
        
        if actual_value and actual_value != 'non_taxable':
            actual_value = str(actual_value)
            tax_group = None
            tax_obj = None

            if actual_value.startswith('group:'):
                tax_group = TaxGroup.objects.filter(
                    pk=actual_value.split(':', 1)[1]
                ).prefetch_related('taxes').first()
            elif actual_value.startswith('tax:'):
                tax_obj = Tax.objects.filter(pk=actual_value.split(':', 1)[1]).first()
            else:
                tax_group = TaxGroup.objects.filter(pk=actual_value).prefetch_related('taxes').first()
                if not tax_group:
                    tax_obj = Tax.objects.filter(pk=actual_value).first()

            if tax_group and tax_group.taxes.exists():
                total_rate = sum(t.rate for t in tax_group.taxes.all())
                option['attrs']['data-rate'] = str(total_rate)
            elif tax_obj:
                option['attrs']['data-rate'] = str(tax_obj.rate or 0)
        
        return option

class TaxSelectionModelFormMixin:
    def clean_prd_tax(self):
        selected_tax = self.cleaned_data.get('prd_tax')
        self.selected_tax_token = selected_tax
        
        return Decimal('0.00')

DISCOUNT_TYPE_CHOICES = [
    ('flat', '₹'),
    ('percent', '%'),
    
]



class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        widgets = {
            # 'customer': forms.Select(attrs={'class': 'form-control vendor-select'}),
            'vendor': forms.Select(attrs={'class': 'form-control vendor-select', 'id': 'vendor_select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            
        }

class PurchaseOrderItemForm(TaxSelectionModelFormMixin, forms.ModelForm):
    # product = forms.ModelChoiceField(queryset=Item.objects.all())
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(widget=forms.HiddenInput(), required=False)
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
        model = PurchaseOrderItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price','prd_tax','description']
        

        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select','data-allow-clear': 'true',}),
            'quantity': forms.NumberInput(attrs={'class': 'qty'}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount', 'value': 0, 'min': 0, 'step': '0.01'}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),  # if you need discount-type class
            # 'prd_tax': Select2Widget(attrs={'class': 'tax-select'}),
            
            'price': forms.NumberInput(attrs={'class': 'price', 'step': '0.0001'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial/default values here
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
            self.fields['o_price'].initial = getattr(self.instance, 'o_price', None)
        # Always ensure hidden fields have valid initial values
        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        self.fields['o_price'].initial = o_price if o_price is not None else 0
        # self.fields['prd_tax'].queryset = TaxGroup.objects.all()
        # self.fields['prd_tax'].label_from_instance = lambda obj: obj.group_name

        # ---------------- TAX PREFILL ----------------
        self.fields['prd_tax'].choices = build_tax_group_choices()
        if self.instance and self.instance.pk:
            saved_tax_id = get_saved_tax_group_id(self.instance)
            if saved_tax_id:
                self.initial['prd_tax'] = saved_tax_id
        # ✅ Step 1: Build a map of UOM names for all items
        # from Item.models import Uom  # ensure import at top or here
        # uom_map = {}
        # uoms = Uom.objects.select_related('name', 'item', 'barcode').all()
        # for u in uoms:
        #     key = f"{u.item.id}_{u.barcode_id}"
        #     uom_map[key] = u.name.name if u.name else ''

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

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['vendor', 'bill_number', 'order', 'date', 'payment_term', 'notes']
        widgets = {
            # 'customer': forms.Select(attrs={'class': 'form-control vendor-select'}),
            'vendor': forms.Select(attrs={'class': 'form-control vendor-select', 'id': 'vendor_select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BillItemForm(TaxSelectionModelFormMixin, forms.ModelForm):
    # product = forms.ModelChoiceField(queryset=Item.objects.all())
    gstinclude = forms.CharField(widget=forms.HiddenInput(), required=False)
    o_price = forms.DecimalField(widget=forms.HiddenInput(), required=False)
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
        model = BillItem
        fields = ['product', 'prd_brcd', 'hsn_code', 'prd_disvalue', 'prd_distype', 'quantity', 'price','prd_tax','description']
        

        widgets = {
            'product': Select2Widget(attrs={'class': 'item_select','data-allow-clear': 'true',}),
            'quantity': forms.NumberInput(attrs={'class': 'qty', 'min': 0}),
            'prd_brcd': forms.TextInput(attrs={'class': 'desc'}),
            'hsn_code': forms.HiddenInput(),
            'prd_disvalue': forms.NumberInput(attrs={'class': 'item-discount', 'value': 0, 'min': 0, 'step': '0.01'}),
            'prd_distype': forms.Select(choices=DISCOUNT_TYPE_CHOICES, attrs={'class': 'discount-type rupee-sign'}),  # if you need discount-type class
            # 'prd_tax': Select2Widget(attrs={'class': 'tax-select'}),
            
            'price': forms.NumberInput(attrs={'class': 'price', 'min': 0, 'step': '0.0001'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial/default values here
        self.fields['quantity'].initial = 1
        self.fields['price'].initial = 0
        self.fields['prd_disvalue'].initial = 0
        if self.instance:
            self.fields['gstinclude'].initial = getattr(self.instance, 'gstinclude', '')
            self.fields['o_price'].initial = getattr(self.instance, 'o_price', None)
        # Always ensure hidden fields have valid initial values
        gst = getattr(self.instance, 'gstinclude', None)
        self.fields['gstinclude'].initial = gst if gst is not None else 'false'

        o_price = getattr(self.instance, 'o_price', None)
        self.fields['o_price'].initial = o_price if o_price is not None else 0
        # self.fields['prd_tax'].queryset = TaxGroup.objects.all()
        # self.fields['prd_tax'].label_from_instance = lambda obj: obj.group_name

        # ---------------- TAX PREFILL ----------------
        self.fields['prd_tax'].choices = build_tax_group_choices()
        if self.instance and self.instance.pk:
            saved_tax_id = get_saved_tax_group_id(self.instance)
            if saved_tax_id:
                self.initial['prd_tax'] = saved_tax_id
        # ✅ Step 1: Build a map of UOM names for all items
        # from Item.models import Uom  # ensure import at top or here
        # uom_map = {}
        # uoms = Uom.objects.select_related('name', 'item', 'barcode').all()
        # for u in uoms:
        #     key = f"{u.item.id}_{u.barcode_id}"
        #     uom_map[key] = u.name.name if u.name else ''

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


class BillPaymentForm(forms.ModelForm):
    class Meta:
        model = BillPayment
        fields = '__all__'


# updated by sree on 27-01-26 for delivery fns
class DeliveryNoteForm(forms.ModelForm):
    class Meta:
        model = DeliveryNote
        fields = ['bill','warehouse', 'delivery_date', 'status', 'received_by', 'notes']
        widgets = {
            'bill': forms.Select(attrs={
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
            'received_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of receiver'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about this delivery...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter bills to show only those with status 'Open'
        self.fields['bill'].queryset = Bill.objects.filter(
            status='Open'
        ).select_related('vendor')
        # All active warehouses
        self.fields['warehouse'].queryset = Warehouse.objects.filter(status=True)


class DeliveryNoteItemForm(forms.ModelForm):
    class Meta:
        model = DeliveryNoteItem
        fields = ['bill_item', 'quantity_delivered', 'notes']
        widgets = {
            'quantity_delivered': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item notes'
            }),
        }


# Formset for delivery note items
DeliveryNoteItemFormSet = inlineformset_factory(
    DeliveryNote,
    DeliveryNoteItem,
    form=DeliveryNoteItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class PurchaseReturnForm(forms.ModelForm):
    class Meta:
        model = PurchaseReturn
        fields = ['bill', 'warehouse', 'date', 'status', 
                  'received_by', 'notes']
        widgets = {
            'bill': forms.Select(attrs={
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
            'received_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of person receiving the return'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes about this return...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For new returns, show bills with confirmed status
        # For existing returns, include the current bill in queryset
        queryset = Bill.objects.filter(status='confirmed').select_related('vendor')
        
        # If editing an existing return, ensure the current bill is included
        if self.instance and self.instance.pk:
            # Create a union of the filtered queryset and the current bill
            from django.db.models import Q
            queryset = Bill.objects.filter(
                Q(status='confirmed') | Q(pk=self.instance.bill_id)
            ).select_related('vendor').distinct()
        
        self.fields['bill'].queryset = queryset
        
        # All active warehouses
        self.fields['warehouse'].queryset = Warehouse.objects.filter(status=True)

