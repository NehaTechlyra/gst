from django import forms
from .models import Expense, ExpenseLine, Vendor
from django.forms import inlineformset_factory
from chart_of_accounts.models import ChartOfAccounts
# Import the Tax model from the Tax app
from Tax.models import Tax
from currencies.models import Currency as MasterCurrency
try:
    from Purchase.models import Vendor as PurchaseVendor
except Exception:
    PurchaseVendor = None

# Optional customer integration
try:
    from customer.models import Customer
except Exception:
    Customer = None

# Common state/UT choices for Source/Destination of supply using full names
STATE_CHOICES = [
    ('', 'Select State/Province'),
    ('Andaman and Nicobar Islands', 'Andaman and Nicobar Islands'),
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Arunachal Pradesh', 'Arunachal Pradesh'),
    ('Assam', 'Assam'),
    ('Bihar', 'Bihar'),
    ('Chandigarh', 'Chandigarh'),
    ('Chhattisgarh', 'Chhattisgarh'),
    ('Dadra and Nagar Haveli and Daman & Diu', 'Dadra and Nagar Haveli and Daman & Diu'),
    ('Delhi', 'Delhi'),
    ('Goa', 'Goa'),
    ('Gujarat', 'Gujarat'),
    ('Haryana', 'Haryana'),
    ('Himachal Pradesh', 'Himachal Pradesh'),
    ('Jammu and Kashmir', 'Jammu and Kashmir'),
    ('Jharkhand', 'Jharkhand'),
    ('Karnataka', 'Karnataka'),
    ('Kerala', 'Kerala'),
    ('Lakshadweep', 'Lakshadweep'),
    ('Maharashtra', 'Maharashtra'),
    ('Meghalaya', 'Meghalaya'),
    ('Manipur', 'Manipur'),
    ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Mizoram', 'Mizoram'),
    ('Nagaland', 'Nagaland'),
    ('Odisha', 'Odisha'),
    ('Punjab', 'Punjab'),
    ('Puducherry', 'Puducherry'),
    ('Rajasthan', 'Rajasthan'),
    ('Sikkim', 'Sikkim'),
    ('Tamil Nadu', 'Tamil Nadu'),
    ('Telangana', 'Telangana'),
    ('Tripura', 'Tripura'),
    ('Uttar Pradesh', 'Uttar Pradesh'),
    ('Uttarakhand', 'Uttarakhand'),
    ('West Bengal', 'West Bengal'),
]

def get_expense_account_choices():
    """
    Returns a hierarchical list of all expense accounts with headers as optgroups
    """
    def get_children(parent_id):
        children = []
        accounts = ChartOfAccounts.objects.filter(
            parent_id=parent_id, 
            type='4',  # Type 4 is for Expenses
            active=True, 
            status=True
        ).order_by('code')
        
        for account in accounts:
            if account.is_header:
                sub_children = get_children(account.pk)
                if sub_children:  # If it has children, create an optgroup
                    children.extend(sub_children)
                else:
                    # If the account is marked as a header but has no children
                    # (possibly due to migration data), treat it as a selectable
                    # leaf so it appears in dropdowns instead of being skipped.
                    children.append((account.code, f"{account.name}"))
            else:
                children.append((account.code, f"{account.name}"))
        return children

    # Get all expense header groups
    expense_groups = ChartOfAccounts.objects.filter(
        type='4',
        is_header=True,
        active=True,
        status=True,
        parent__isnull=False  # Skip the root expense account
    ).order_by('code')

    choices = []
    for group in expense_groups:
        sub_choices = get_children(group.pk)
        if sub_choices:
            choices.append((group.name, sub_choices))
    
    return choices

def get_payment_account_choices():
    """
    Returns a hierarchical list of all non-expense accounts
    """
    def get_children(parent_id, account_type):
        children = []
        accounts = ChartOfAccounts.objects.filter(
            parent_id=parent_id,
            type=account_type,
            active=True,
            status=True
        ).order_by('code')
        
        for account in accounts:
            if account.is_header:
                sub_children = get_children(account.pk, account_type)
                if sub_children:  # If it has children, create an optgroup
                    children.extend(sub_children)
                else:
                    # See note above: if header flag is set but no children
                    # exist, show it as a selectable option so dropdowns are
                    # still usable after migrations that incorrectly set
                    # `is_header=True` for leaf accounts.
                    children.append((account.code, f" {account.name}"))
            else:
                children.append((account.code, f" {account.name}"))
        return children

    choices = []
    
    # Account type mapping
    account_types = {
        '1': 'Assets',
        '2': 'Liabilities',
        '3': 'Income',
        '5': 'Equity'
    }

    # Get all main groups for each account type except expenses
    for type_code, type_name in account_types.items():
        # Get main groups for this account type
        main_groups = ChartOfAccounts.objects.filter(
            type=type_code,
            is_header=True,
            active=True,
            status=True,
            parent__isnull=False  # Skip root accounts
        ).order_by('code')

        type_choices = []
        for group in main_groups:
            sub_choices = get_children(group.pk, type_code)
            if sub_choices:
                type_choices.append((group.name, sub_choices))

        if type_choices:
            choices.extend(type_choices)
    
    return choices

class ExpenseLineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up the account field with expense accounts
        self.fields['account'] = forms.ChoiceField(
            widget=forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Search Expense Account...'
            })
        )
        self.fields['account'].choices = [('', 'Select an expense account')] + get_expense_account_choices()
        
        # Populate tax choices from Tax model
        # Use verbose tax labels so the JS can parse type and rate (we'll
        # render a compact view in Select2 via template functions)
        tax_choices = [('', '---------')] + [
            (str(t.pk), f"{t.taxname} - {t.taxtype} ({t.rate}%)") 
            for t in Tax.objects.all().order_by('taxname')
        ]
        self.fields['tax'] = forms.ChoiceField(
            choices=tax_choices,
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Select Tax'
            })
        )

        # If this form is bound to an existing ExpenseLine instance, set initial values
        try:
            if getattr(self, 'instance', None) and getattr(self.instance, 'pk', None):
                # account field stores account.code as the value
                acct = getattr(self.instance, 'account', None)
                if acct:
                    self.fields['account'].initial = acct.code
                    # also set form initial so template rendering picks it up
                    self.initial['account'] = acct.code
                # tax field stores tax.pk as string
                tx = getattr(self.instance, 'tax', None)
                if tx:
                    self.fields['tax'].initial = str(tx.pk)
                    self.initial['tax'] = str(tx.pk)
        except Exception:
            pass

    def clean_account(self):
        account_code = self.cleaned_data['account']
        try:
            # Allow selecting accounts even if they are marked as headers
            # (some migrations may set many accounts as headers). Match by code
            # and account type, and ensure account is active.
            return ChartOfAccounts.objects.get(code=account_code, type='4', active=True, status=True)
        except ChartOfAccounts.DoesNotExist:
            raise forms.ValidationError("Invalid expense account selected.")

    def clean_tax(self):
        """Resolve tax selection from Tax model"""
        tax_val = self.cleaned_data.get('tax')
        if not tax_val:
            return None

        try:
            return Tax.objects.get(pk=int(tax_val))
        except Exception:
            raise forms.ValidationError('Invalid tax selected.')

    class Meta:
        model = ExpenseLine
        fields = ['account', 'notes', 'amount', 'tax']
        widgets = {
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax': forms.Select(attrs={'class': 'form-select select2'})
        }

class ExpenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        self.fields['currency'] = forms.ChoiceField(
            choices=self._get_currency_choices(),
            widget=forms.Select(attrs={'class': 'form-select'})
        )

        # Set up the paid_through field with all non-expense accounts
        self.fields['paid_through'] = forms.ChoiceField(
            widget=forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Search Payment Account...'
            })
        )
        self.fields['paid_through'].choices = [('', 'Select payment account')] + get_payment_account_choices()
        # If editing an instance, pre-select the paid_through using the account code
        try:
            if getattr(self, 'instance', None) and getattr(self.instance, 'paid_through', None):
                code_val = getattr(self.instance.paid_through, 'code', '')
                self.fields['paid_through'].initial = code_val
                self.initial['paid_through'] = code_val
        except Exception:
            pass

        # Populate vendor choices from Purchase.Vendor if available
        vendor_required = True
        gst_treatment = self.initial.get('gst_treatment') or self.data.get('gst_treatment')
        if gst_treatment == 'out_of_scope':
            vendor_required = False

        if PurchaseVendor is not None:
            vendor_choices = [('', '---------')] + [
                (str(v.pk), str(v))
                for v in PurchaseVendor.objects.all().order_by('vendor_code')
            ]
            # If editing an existing expense that uses an internal Vendor, make sure the vendor appears in choices
            try:
                if getattr(self, 'instance', None) and getattr(self.instance, 'vendor', None):
                    ev = self.instance.vendor
                    # append if not present
                    if not any(str(ev.pk) == str(c[0]) for c in vendor_choices):
                        vendor_choices.append((str(ev.pk), str(ev)))
            except Exception:
                pass

            self.fields['vendor'] = forms.ChoiceField(
                choices=vendor_choices,
                required=vendor_required,
                widget=forms.Select(attrs={
                    'class': 'form-select select2',
                    'data-placeholder': 'Search Vendor...'
                })
            )
            # If editing, set initial vendor selection
            try:
                if getattr(self, 'instance', None) and getattr(self.instance, 'vendor', None):
                    vval = str(self.instance.vendor.pk)
                    self.fields['vendor'].initial = vval
                    self.initial['vendor'] = vval
                    # also ensure vendor_gstin populated from instance
                    if hasattr(self.instance, 'vendor_gstin'):
                        self.initial['vendor_gstin'] = self.instance.vendor_gstin
            except Exception:
                pass

            # If vendor_gstin still empty, try to derive from PurchaseVendor record with same name
            try:
                if PurchaseVendor is not None and getattr(self, 'instance', None) and getattr(self.instance, 'vendor', None):
                    if not self.initial.get('vendor_gstin'):
                        pv = PurchaseVendor.objects.filter(vendor_code=self.instance.vendor.vendor_code).first() if hasattr(self.instance.vendor, 'vendor_code') else None
                        if pv:
                            # try multiple possible field names for GSTIN on PurchaseVendor
                            gst = None
                            for attr in ('gstin', 'vendor_gstin', 'gstin_number', 'gst_no', 'gst_number', 'gst'):
                                gst = getattr(pv, attr, None)
                                if gst:
                                    break
                            if gst:
                                self.initial['vendor_gstin'] = gst
                                try:
                                    self.fields['vendor_gstin'].initial = gst
                                except Exception:
                                    pass
            except Exception:
                pass

        # Optional: Populate customer choices from customer.Customer if available
        customer_required = True
        if gst_treatment == 'out_of_scope':
            customer_required = False

        if Customer is not None:
            cust_choices = [('', '---------')] + [
                (str(c.pk), str(c)) for c in Customer.objects.filter(is_active=True, is_draft=False).order_by('customer_code')
            ]
            self.fields['customer'] = forms.ChoiceField(
                choices=cust_choices,
                required=customer_required,
                widget=forms.Select(attrs={
                    'class': 'form-select select2',
                    'data-placeholder': 'Search Customer...'
                })
            )
            # Preselect customer if editing and stored value matches a pk
            try:
                if getattr(self, 'instance', None) and self.instance.customer:
                    # instance.customer stores the PK string (if saved that way)
                    self.fields['customer'].initial = str(self.instance.customer)
                    self.initial['customer'] = str(self.instance.customer)
            except Exception:
                pass

    def _get_selected_currency_code(self):
        if self.is_bound:
            return (self.data.get(self.add_prefix('currency')) or '').strip().upper()

        current_value = getattr(getattr(self, 'instance', None), 'currency', '') or self.initial.get('currency', '')
        return str(current_value or '').strip().upper()

    def _get_currency_choices(self):
        choices = [('', 'Select currency')]
        selected_code = self._get_selected_currency_code()
        existing_codes = set()

        if self.company:
            company_currencies = MasterCurrency.objects.filter(
                company=self.company,
                is_active=True,
            ).order_by('-is_base', 'code')

            for currency in company_currencies:
                code = (currency.code or '').strip().upper()
                if not code:
                    continue
                label = f"{code} - {currency.name}" if currency.name and currency.name.strip().upper() != code else code
                choices.append((code, label))
                existing_codes.add(code)

        if selected_code and selected_code not in existing_codes:
            choices.append((selected_code, selected_code))

        return choices

    def clean_paid_through(self):
        account_code = self.cleaned_data['paid_through']
        try:
            # Allow payment accounts that might be headers due to migration
            return ChartOfAccounts.objects.get(
                code=account_code,
                active=True,
                status=True
            )
        except ChartOfAccounts.DoesNotExist:
            raise forms.ValidationError("Invalid payment account selected.")

    def clean_vendor_gstin(self):
        """Validate the GSTIN format"""
        gstin = self.cleaned_data.get('vendor_gstin')
        if gstin:
            gstin = gstin.strip().upper()
            if len(gstin) != 15:
                raise forms.ValidationError('GSTIN must be exactly 15 characters long')
        return gstin

    def clean_currency(self):
        currency_code = (self.cleaned_data.get('currency') or '').strip().upper()
        if not currency_code:
            raise forms.ValidationError('Currency is required.')

        if self.company and not MasterCurrency.objects.filter(
            company=self.company,
            code__iexact=currency_code,
            is_active=True,
        ).exists():
            instance_currency = str(getattr(getattr(self, 'instance', None), 'currency', '') or '').strip().upper()
            if currency_code != instance_currency:
                raise forms.ValidationError('Invalid currency selected.')

        return currency_code

    def clean_customer(self):
        """Convert customer selection to a string that can be used to retrieve the customer later"""
        customer_val = self.cleaned_data.get('customer')
        if not customer_val:
            return ''
        return customer_val

    def clean_vendor(self):
        """Resolve vendor selection from Purchase.Vendor to an expenses.Vendor instance.
        If a matching expenses.Vendor doesn't exist, create one using basic fields.
        """
        vendor_val = self.cleaned_data.get('vendor')
        if not vendor_val:
            return None

        # If PurchaseVendor is available and the value corresponds to it, map/create
        if PurchaseVendor is not None:
            try:
                pv = PurchaseVendor.objects.get(pk=int(vendor_val))
            except Exception:
                # Not a Purchase vendor id; maybe an expenses.Vendor code
                try:
                    return Vendor.objects.get(pk=int(vendor_val))
                except Exception:
                    raise forms.ValidationError('Invalid vendor selected.')

            # Now find or create an expenses.Vendor with the same name
            ev, created = Vendor.objects.get_or_create(
                name=str(pv),
                defaults={
                    'contact': getattr(pv, 'phone', '') or '',
                    'email': getattr(pv, 'email', '') or ''
                }
            )
            return ev

        # Fallback: try to return an expenses.Vendor by pk
        try:
            return Vendor.objects.get(pk=int(vendor_val))
        except Exception:
            raise forms.ValidationError('Invalid vendor selected.')

    class Meta:
        model = Expense
        fields = [
            'date', 'currency', 'fx_rate_to_base', 'fx_rate_date', 'paid_through', 'expense_type',
            'sac_hsn', 'vendor', 'vendor_gstin', 'gst_treatment', 'place_of_supply',
            'destination_of_supply', 'reverse_charge', 'amount_is',
            'invoice_number', 'customer', 'total_amount_base'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'paid_through': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Search Payment Account...'}),
            'fx_rate_to_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'fx_rate_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expense_type': forms.RadioSelect(),
            'sac_hsn': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.Select(attrs={'class': 'form-select select2'}),
            'gst_treatment': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Select GST Treatment'
            }),
            'place_of_supply': forms.Select(choices=STATE_CHOICES, attrs={'class': 'form-select select2', 'data-placeholder': 'Place of Supply'}),
            'destination_of_supply': forms.Select(choices=STATE_CHOICES, attrs={'class': 'form-select select2', 'data-placeholder': 'Destination of Supply'}),
            'reverse_charge': forms.CheckboxInput(),
            'amount_is': forms.RadioSelect(),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'fx_rate_to_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '1.000000'}),
            'fx_rate_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_amount_base': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

# Create the inline formset factory for expense lines
ExpenseLineFormSet = inlineformset_factory(
    Expense,
    ExpenseLine,
    form=ExpenseLineForm,
    extra=1,  # Number of empty forms to display
    can_delete=True  # Allow deleting lines
)
