from django import forms
from .models import JournalEntry, JournalLine
from chart_of_accounts.models import ChartOfAccounts

def get_account_choices():
    """
    Returns a list of (header, [(id, name)]) for accounts, with all account types as headers
    and their respective child accounts nested under them.
    """
    def collect_leaves(root_id, indent_level=0):
        """
        Collect leaf accounts under the given root (flattening any header-only levels)
        and return a list of (id, label) pairs with indentation applied.
        """
        leaves = []

        def _collect(parent, level):
            qs = ChartOfAccounts.objects.filter(parent_id=parent, active=True, status=True).order_by('code')
            for acct in qs:
                # If this account has children, recurse; otherwise treat as leaf
                has_children = ChartOfAccounts.objects.filter(parent_id=acct.id, active=True, status=True).exists()
                if has_children:
                    _collect(acct.id, level + 1)
                else:
                    indent = '    ' * level
                    leaves.append((acct.id, f"{indent}{acct.name}"))

        _collect(root_id, indent_level)
        return leaves

    # Build top-level choices: for each top-level account under None, if it has
    # leaves, present as optgroup (label, [ (id,label), ... ]). If it has no
    # leaves (a selectable leaf), include it as a (id,label) tuple.
    choices = []
    top_qs = ChartOfAccounts.objects.filter(parent_id=None, active=True, status=True).order_by('code')
    for top in top_qs:
        # For each child of this top-level node, gather leaves grouped by immediate child
        children = ChartOfAccounts.objects.filter(parent_id=top.id, active=True, status=True).order_by('code')
        group_items = []
        for child in children:
            # collect leaves under this child
            leaves = collect_leaves(child.id, indent_level=1)
            if leaves:
                # Use child.name as sub-group label (optgroup within top group isn't supported by HTML)
                # so we append leaves directly under top as one optgroup
                group_items.extend(leaves)
            else:
                # Child is a direct selectable leaf
                group_items.append((child.id, child.name))

        if group_items:
            # Create an optgroup for the top-level node
            choices.append((top.name, group_items))
        else:
            # No child leaves found; if top itself is a leaf, include it as selectable
            has_children = ChartOfAccounts.objects.filter(parent_id=top.id, active=True, status=True).exists()
            if not has_children:
                choices.append((top.id, top.name))

    return choices

class JournalEntryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  # Only set default date for new instances
            from datetime import date
            self.initial['date'] = date.today()
        # Make narration optional on the form (no client-side required enforcement)
        if 'narration' in self.fields:
            self.fields['narration'].required = False

    class Meta:
        model = JournalEntry
        fields = ['date', 'reference', 'narration']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'narration': forms.Textarea(attrs={'rows': 3}),
        }

class JournalLineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].choices = [('', '---------')] + get_account_choices()

    class Meta:
        model = JournalLine
        fields = ['account', 'description', 'debit', 'credit']
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select select2',
                'style': 'width: 100%;'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'debit': forms.NumberInput(attrs={
                'class': 'form-control text-end',
                'step': '0.01',
                'min': '0'
            }),
            'credit': forms.NumberInput(attrs={
                'class': 'form-control text-end',
                'step': '0.01',
                'min': '0'
            }),
        }

class JournalLineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """
        Validate that total debits equals total credits
        and at least two lines are entered
        """
        if any(self.errors):
            return

        total_debit = sum(form.cleaned_data.get('debit', 0) 
                         for form in self.forms if not self._should_delete_form(form))
        total_credit = sum(form.cleaned_data.get('credit', 0) 
                          for form in self.forms if not self._should_delete_form(form))

        if total_debit != total_credit:
            raise forms.ValidationError('Total debits must equal total credits')

        valid_forms = [form for form in self.forms 
                      if not self._should_delete_form(form) and form.is_valid()]
        if len(valid_forms) < 2:
            raise forms.ValidationError('At least two lines are required')