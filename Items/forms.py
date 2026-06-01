
from django import forms
from Items.models import Item,Barcode
from .models import Uom,Uom_name
from unit.models import Unit
from Purchase.models import Vendor
from Tax.models import Tax, TaxGroup

from chart_of_accounts.models import ChartOfAccounts


NEW_CURRENCY_VALUE = "__new_currency__"
NEW_CURRENCY_LABEL = "+ New Currency"


def _append_new_currency_choice(field):
    choices = list(field.choices)
    if not any(str(choice[0]) == NEW_CURRENCY_VALUE for choice in choices):
        choices.append((NEW_CURRENCY_VALUE, NEW_CURRENCY_LABEL))
        field.choices = choices

#by adarsh
def get_equity_account_choices():
    """Return all equity accounts (type=5) for opening stock posting"""
    equity_accounts = ChartOfAccounts.objects.filter(
        type='5',  # Equity type
        active=True,
        status=True,
        is_header=False  # Only leaf accounts, not headers
    ).order_by('code')
    
    choices = [('', 'Select equity account')]
    for account in equity_accounts:
        choices.append((account.id, account.name))
    
    return choices


def get_default_equity_account():
    """Get the first/main equity account (usually Owner's Capital or similar)"""
    # Try to find "Owner's Capital" or similar
    for name_pattern in ['capital', 'owner', 'proprietor']:
        account = ChartOfAccounts.objects.filter(
            type='5',
            name__icontains=name_pattern,
            active=True,
            status=True,
            is_header=False
        ).order_by('code').first()
        if account:
            return account.id
    
    # Fallback: return first equity account
    account = ChartOfAccounts.objects.filter(
        type='5',
        active=True,
        status=True,
        is_header=False
    ).order_by('code').first()
    
    return account.id if account else None
#by adarsh

def get_sales_account_choices():
    """
    Returns a hierarchical list of all income (sales) accounts with headers as optgroups
    """
    def get_children(parent_id):
        children = []
        accounts = ChartOfAccounts.objects.filter(
            parent_id=parent_id,
            type='3',  # Type 3 is for Income (Sales)
            active=True,
            status=True
        ).order_by('code')
        for account in accounts:
            if account.is_header:
                sub_children = get_children(account.pk)
                if sub_children:
                    children.extend(sub_children)
                else:
                    # Header marked but no children: make it selectable
                    children.append((account.code, f" {account.name}"))
            else:
                # Show name only (no code) to match expense 'paid_through' display
                children.append((account.code, f" {account.name}"))
        return children

    # Get all income header groups
    income_groups = ChartOfAccounts.objects.filter(
        type='3',
        is_header=True,
        active=True,
        status=True,
        parent__isnull=False
    ).order_by('code')

    choices = []
    for group in income_groups:
        sub_choices = get_children(group.pk)
        if sub_choices:
            choices.append((group.name, sub_choices))
    return choices


def get_non_expense_account_choices():
    """Return hierarchical choices for non-expense account types (Assets, Liabilities, Income, Equity)
    Mirrors the logic used by expenses.get_payment_account_choices so the UI shows the full chart.
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
                if sub_children:
                    children.extend(sub_children)
                else:
                    children.append((account.code, f" {account.name}"))
            else:
                # keep label consistent with expenses: show only name (optgroup will provide grouping)
                children.append((account.code, f" {account.name}"))
        return children

    choices = []
    account_types = {'1': 'Assets', '2': 'Liabilities', '3': 'Income', '5': 'Equity'}

    for type_code, type_name in account_types.items():
        main_groups = ChartOfAccounts.objects.filter(
            type=type_code,
            is_header=True,
            active=True,
            status=True,
            parent__isnull=False
        ).order_by('code')

        type_choices = []
        for group in main_groups:
            sub_choices = get_children(group.pk, type_code)
            if sub_choices:
                type_choices.append((group.name, sub_choices))

        if type_choices:
            choices.extend(type_choices)

    return choices


def get_expense_account_choices():
    """Returns hierarchical expense account choices (type=4) similar to expenses.ExpensesLineForm"""
    def get_children(parent_id):
        children = []
        accounts = ChartOfAccounts.objects.filter(
            parent_id=parent_id,
            type='4',  # Expenses
            active=True,
            status=True
        ).order_by('code')

        for account in accounts:
            if account.is_header:
                sub_children = get_children(account.pk)
                if sub_children:
                    children.extend(sub_children)
                else:
                    children.append((account.code, f"{account.name}"))
            else:
                children.append((account.code, f"{account.name}"))
        return children

    expense_groups = ChartOfAccounts.objects.filter(
        type='4',
        is_header=True,
        active=True,
        status=True,
        parent__isnull=False
    ).order_by('code')

    choices = []
    for group in expense_groups:
        sub_choices = get_children(group.pk)
        if sub_choices:
            choices.append((group.name, sub_choices))
    return choices

class ItemForm(forms.ModelForm):
    sales_account = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Search Sales Account...'
        })
    )
    purchase_account = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Search Expense Account...'
        })
    )
    opening_stock_equity_account = forms.ChoiceField(#by adarsh
        required=False,
        label='Opening Stock Equity Account',
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Select equity account for opening balance...'
        }),
        help_text='Select the equity account to post opening stock amount'
    )#by adarsh


    class Meta:
        model = Item
        exclude = ['created_by', 'updated_by', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up the sales_account field with all non-expense accounts (match expense paid_through)
        self.fields['sales_account'].choices = [('', 'Select sales account')] + get_non_expense_account_choices()

        # Set up the purchase_account field with all expense accounts (match ExpenseLineForm choices)
        self.fields['purchase_account'].choices = [('', 'Select an expense account')] + get_expense_account_choices()

        # Purchase account: prefer saved value when editing; otherwise try to default to Cost of Goods Sold
        if getattr(self, 'instance', None) and getattr(self.instance, 'purchase_account', None):
            # preserve whatever is stored (could be a name or a code). If it's a
            # stored name, try to resolve to an account.code so the select shows it.
            saved = self.instance.purchase_account
            try:
                acct = ChartOfAccounts.objects.filter(code=str(saved), active=True, status=True).first()
                if acct:
                    sel_val = acct.code
                else:
                    acct2 = ChartOfAccounts.objects.filter(name__iexact=str(saved), active=True, status=True).first()
                    sel_val = acct2.code if acct2 else saved
            except Exception:
                sel_val = saved
            self.fields['purchase_account'].initial = sel_val
            self.initial['purchase_account'] = sel_val
        else:
            try:
                # prefer a ChartOfAccounts match and use its code as the initial value
                cogs = ChartOfAccounts.objects.filter(name__icontains='Cost of Goods Sold', type='4', active=True, status=True).first()
                if cogs:
                    self.fields['purchase_account'].initial = cogs.code
                    self.initial['purchase_account'] = cogs.code
                else:
                    # fallback to the common name string for backward compatibility
                    self.fields['purchase_account'].initial = 'Cost of Goods Sold'
                    self.initial['purchase_account'] = 'Cost of Goods Sold'
            except Exception:
                pass

        # Sales account: prefer saved value when editing; otherwise default to Sales account if present
        if getattr(self, 'instance', None) and getattr(self.instance, 'sales_account', None):
            saved = self.instance.sales_account
            try:
                acct = ChartOfAccounts.objects.filter(code=str(saved), active=True, status=True).first()
                if acct:
                    sel_val = acct.code
                else:
                    acct2 = ChartOfAccounts.objects.filter(name__iexact=str(saved), active=True, status=True).first()
                    sel_val = acct2.code if acct2 else saved
            except Exception:
                sel_val = saved
            self.fields['sales_account'].initial = sel_val
            self.initial['sales_account'] = sel_val
        else:
            try:
                # Try a few fallbacks to locate the core Sales account
                sales_acct = ChartOfAccounts.objects.filter(name__iexact='Sales', type='3', active=True, status=True).first()
                if not sales_acct:
                    sales_acct = ChartOfAccounts.objects.filter(name__icontains='Sales', type='3', active=True, status=True).first()
                if not sales_acct:
                    # common default code used in migrations
                    sales_acct = ChartOfAccounts.objects.filter(code='30101', active=True, status=True).first()

                if sales_acct:
                    sel_code = sales_acct.code
                    # Ensure the code appears in the available choices (some chart setups may omit it)
                    choices = list(self.fields['sales_account'].choices)
                    found = False
                    for ch in choices:
                        # optgroup -> (label, [(val,label),...]) or simple -> (val,label)
                        if isinstance(ch[1], (list, tuple)):
                            for val, lbl in ch[1]:
                                if str(val) == str(sel_code):
                                    found = True
                                    break
                            if found:
                                break
                        else:
                            if str(ch[0]) == str(sel_code):
                                found = True
                                break

                    if not found:
                        # Insert into the correct optgroup (prefer parent's group) so it
                        # appears selected without moving it to the very top of the list.
                        parent_name = sales_acct.parent.name if getattr(sales_acct, 'parent', None) else None
                        new_choice = (sel_code, f" {sales_acct.name}")
                        inserted = False

                        for i, ch in enumerate(choices):
                            # optgroup entries are (label, [(val,label),...])
                            if isinstance(ch[1], (list, tuple)):
                                if parent_name and ch[0] == parent_name:
                                    ch[1].insert(0, new_choice)
                                    inserted = True
                                    break

                        if not inserted:
                            # try to find an Income-related group as a sensible fallback
                            for i, ch in enumerate(choices):
                                if isinstance(ch[1], (list, tuple)) and ("Income" in ch[0] or "Sales" in ch[0]):
                                    ch[1].insert(0, new_choice)
                                    inserted = True
                                    break

                        if not inserted:
                            # last resort: add into the last optgroup if available
                            if choices and isinstance(choices[-1][1], (list, tuple)):
                                choices[-1][1].append(new_choice)
                            else:
                                # very fallback: insert after placeholder
                                choices.insert(1, new_choice)

                        self.fields['sales_account'].choices = choices

                    self.fields['sales_account'].initial = sel_code
                    self.initial['sales_account'] = sel_code
                else:
                    self.fields['sales_account'].initial = 'Sales'
                    self.initial['sales_account'] = 'Sales'
            except Exception:
                pass
        
        # by adarsh: Setup opening_stock_equity_account field
        self.fields['opening_stock_equity_account'].choices = get_equity_account_choices()
        
        # Pre-fill opening stock equity account from existing journal entry when editing
        if getattr(self, 'instance', None) and self.instance.pk and self.instance.name:
            try:
                from journal.models import JournalEntry, JournalLine
                entry_reference = f"OPENING_STOCK_{self.instance.name.upper()}"
                existing_entry = JournalEntry.objects.filter(
                    reference=entry_reference
                ).exclude(
                    narration__startswith='Reversal of'
                ).order_by('-id').first()
                
                if existing_entry:
                    # The equity account is in the credit line (credit > 0)
                    credit_line = JournalLine.objects.filter(journal=existing_entry, credit__gt=0).first()
                    if credit_line:
                        self.fields['opening_stock_equity_account'].initial = credit_line.account_id
                        self.initial['opening_stock_equity_account'] = credit_line.account_id
            except Exception:
                pass
        # Ensure FK fields load from full queryset
        # self.fields['intra_tax'].queryset = Tax.objects.all()
        # self.fields['inter_tax_group'].queryset = TaxGroup.objects.all()
        print("Intra Tax Queryset IDs:", list(self.fields['intra_tax'].queryset.values_list('id', flat=True)))
        print("Inter Tax Group Queryset IDs:", list(self.fields['inter_tax_group'].queryset.values_list('id', flat=True)))

    def clean(self):
        cleaned_data = super().clean()
        sales_info = cleaned_data.get('sales_info')
        purchase_info = cleaned_data.get('purchase_info')

        if not sales_info and not purchase_info:
            raise forms.ValidationError("At least one of Sales Information or Purchase Information must be selected.")

        return cleaned_data


class UomForm(forms.ModelForm):
    class Meta:
        model = Uom_name
        fields = '__all__'


class VendorForm(forms.ModelForm):
    # Provide same country choices used elsewhere so modal select is populated
    COUNTRY_CHOICES = [
        ('', 'Select country'),
        ('Afghanistan','Afghanistan'),
        ('Albania','Albania'),
        ('Algeria','Algeria'),
        ('Andorra','Andorra'),
        ('Angola','Angola'),
        ('Antigua and Barbuda','Antigua and Barbuda'),
        ('Argentina','Argentina'),
        ('Armenia','Armenia'),
        ('Australia','Australia'),
        ('Austria','Austria'),
        ('Azerbaijan','Azerbaijan'),
        ('Bahamas','Bahamas'),
        ('Bahrain','Bahrain'),
        ('Bangladesh','Bangladesh'),
        ('Barbados','Barbados'),
        ('Belarus','Belarus'),
        ('Belgium','Belgium'),
        ('Belize','Belize'),
        ('Benin','Benin'),
        ('Bhutan','Bhutan'),
        ('Bolivia','Bolivia'),
        ('Bosnia and Herzegovina','Bosnia and Herzegovina'),
        ('Botswana','Botswana'),
        ('Brazil','Brazil'),
        ('Brunei','Brunei'),
        ('Bulgaria','Bulgaria'),
        ('Burkina Faso','Burkina Faso'),
        ('Burundi','Burundi'),
        ('Cabo Verde','Cabo Verde'),
        ('Cambodia','Cambodia'),
        ('Cameroon','Cameroon'),
        ('Canada','Canada'),
        ('Central African Republic','Central African Republic'),
        ('Chad','Chad'),
        ('Chile','Chile'),
        ('China','China'),
        ('Colombia','Colombia'),
        ('Comoros','Comoros'),
        ('Costa Rica','Costa Rica'),
        ('Côte d\'Ivoire','Côte d\'Ivoire'),
        ('Croatia','Croatia'),
        ('Cuba','Cuba'),
        ('Cyprus','Cyprus'),
        ('Czechia','Czechia'),
        ('Denmark','Denmark'),
        ('Djibouti','Djibouti'),
        ('Dominica','Dominica'),
        ('Dominican Republic','Dominican Republic'),
        ('Ecuador','Ecuador'),
        ('Egypt','Egypt'),
        ('El Salvador','El Salvador'),
        ('Equatorial Guinea','Equatorial Guinea'),
        ('Eritrea','Eritrea'),
        ('Estonia','Estonia'),
        ('Eswatini','Eswatini'),
        ('Ethiopia','Ethiopia'),
        ('Fiji','Fiji'),
        ('Finland','Finland'),
        ('France','France'),
        ('Gabon','Gabon'),
        ('Gambia','Gambia'),
        ('Georgia','Georgia'),
        ('Germany','Germany'),
        ('Ghana','Ghana'),
        ('Greece','Greece'),
        ('Grenada','Grenada'),
        ('Guatemala','Guatemala'),
        ('Guinea','Guinea'),
        ('Guinea-Bissau','Guinea-Bissau'),
        ('Guyana','Guyana'),
        ('Haiti','Haiti'),
        ('Honduras','Honduras'),
        ('Hungary','Hungary'),
        ('Iceland','Iceland'),
        ('India','India'),
        ('Indonesia','Indonesia'),
        ('Iran','Iran'),
        ('Iraq','Iraq'),
        ('Ireland','Ireland'),
        ('Israel','Israel'),
        ('Italy','Italy'),
        ('Jamaica','Jamaica'),
        ('Japan','Japan'),
        ('Jordan','Jordan'),
        ('Kazakhstan','Kazakhstan'),
        ('Kenya','Kenya'),
        ('Kiribati','Kiribati'),
        ('Korea, North','Korea, North'),
        ('Korea, South','Korea, South'),
        ('Kosovo','Kosovo'),
        ('Kuwait','Kuwait'),
        ('Kyrgyzstan','Kyrgyzstan'),
        ('Laos','Laos'),
        ('Latvia','Latvia'),
        ('Lebanon','Lebanon'),
        ('Lesotho','Lesotho'),
        ('Liberia','Liberia'),
        ('Libya','Libya'),
        ('Liechtenstein','Liechtenstein'),
        ('Lithuania','Lithuania'),
        ('Luxembourg','Luxembourg'),
        ('Madagascar','Madagascar'),
        ('Malawi','Malawi'),
        ('Malaysia','Malaysia'),
        ('Maldives','Maldives'),
        ('Mali','Mali'),
        ('Malta','Malta'),
        ('Marshall Islands','Marshall Islands'),
        ('Mauritania','Mauritania'),
        ('Mauritius','Mauritius'),
        ('Mexico','Mexico'),
        ('Micronesia','Micronesia'),
        ('Moldova','Moldova'),
        ('Monaco','Monaco'),
        ('Mongolia','Mongolia'),
        ('Montenegro','Montenegro'),
        ('Morocco','Morocco'),
        ('Mozambique','Mozambique'),
        ('Myanmar','Myanmar'),
        ('Namibia','Namibia'),
        ('Nauru','Nauru'),
        ('Nepal','Nepal'),
        ('Netherlands','Netherlands'),
        ('New Zealand','New Zealand'),
        ('Nicaragua','Nicaragua'),
        ('Niger','Niger'),
        ('Nigeria','Nigeria'),
        ('North Macedonia','North Macedonia'),
        ('Norway','Norway'),
        ('Oman','Oman'),
        ('Pakistan','Pakistan'),
        ('Palau','Palau'),
        ('Panama','Panama'),
        ('Papua New Guinea','Papua New Guinea'),
        ('Paraguay','Paraguay'),
        ('Peru','Peru'),
        ('Philippines','Philippines'),
        ('Poland','Poland'),
        ('Portugal','Portugal'),
        ('Qatar','Qatar'),
        ('Romania','Romania'),
        ('Russia','Russia'),
        ('Rwanda','Rwanda'),
        ('Saint Kitts and Nevis','Saint Kitts and Nevis'),
        ('Saint Lucia','Saint Lucia'),
        ('Saint Vincent and the Grenadines','Saint Vincent and the Grenadines'),
        ('Samoa','Samoa'),
        ('San Marino','San Marino'),
        ('Sao Tome and Principe','Sao Tome and Principe'),
        ('Saudi Arabia','Saudi Arabia'),
        ('Senegal','Senegal'),
        ('Serbia','Serbia'),
        ('Seychelles','Seychelles'),
        ('Sierra Leone','Sierra Leone'),
        ('Singapore','Singapore'),
        ('Slovakia','Slovakia'),
        ('Slovenia','Slovenia'),
        ('Solomon Islands','Solomon Islands'),
        ('Somalia','Somalia'),
        ('South Africa','South Africa'),
        ('South Sudan','South Sudan'),
        ('Spain','Spain'),
        ('Sri Lanka','Sri Lanka'),
        ('Sudan','Sudan'),
        ('Suriname','Suriname'),
        ('Sweden','Sweden'),
        ('Switzerland','Switzerland'),
        ('Syria','Syria'),
        ('Taiwan','Taiwan'),
        ('Tajikistan','Tajikistan'),
        ('Tanzania','Tanzania'),
        ('Thailand','Thailand'),
        ('Timor-Leste','Timor-Leste'),
        ('Togo','Togo'),
        ('Tonga','Tonga'),
        ('Trinidad and Tobago','Trinidad and Tobago'),
        ('Tunisia','Tunisia'),
        ('Turkey','Turkey'),
        ('Turkmenistan','Turkmenistan'),
        ('Tuvalu','Tuvalu'),
        ('Uganda','Uganda'),
        ('Ukraine','Ukraine'),
        ('United Arab Emirates','United Arab Emirates'),
        ('United Kingdom','United Kingdom'),
        ('United States','United States'),
        ('Uruguay','Uruguay'),
        ('Uzbekistan','Uzbekistan'),
        ('Vanuatu','Vanuatu'),
        ('Vatican City','Vatican City'),
        ('Venezuela','Venezuela'),
        ('Vietnam','Vietnam'),
        ('Yemen','Yemen'),
        ('Zambia','Zambia'),
        ('Zimbabwe','Zimbabwe'),
        ('Other','Other'),
    ]
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, required=False)

    class Meta:
        model = Vendor
        exclude = ['crtd_by', 'updt_by']
        widgets = {
            'country': forms.Select(attrs={'class': 'form-control select2','data-placeholder':'Select','style':'width:100%'}),
        }
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        # Configure currency choices from the active company and add the shared "new currency" action.
        try:
            from currencies.models import Currency
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

class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = [
             'unit_name'
        ]