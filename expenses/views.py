from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
import json
import logging
from .models import Expense, ExpenseLine
from django.core.paginator import Paginator
from django.http import JsonResponse
from .forms import ExpenseForm, ExpenseLineFormSet, ExpenseLineForm
from django.forms import inlineformset_factory
from Tax.models import Tax
from journal.models import JournalEntry, JournalLine
from chart_of_accounts.models import ChartOfAccounts
from chart_of_accounts.services import get_company_tax_type, resolve_tax_account, normalize_tax_code
from django.db import IntegrityError
from company.models import Company
from currencies.models import Currency as MasterCurrency
from Purchase.permissions import (
    can_view_purchase_expenses, can_create_purchase_expenses,
    can_edit_purchase_expenses, can_delete_purchase_expenses
)
from currencies.services import get_effective_rate_to_base, scale_amount_for_journal


logger = logging.getLogger(__name__)

def _get_tax_type_code(tax):
    return normalize_tax_code(getattr(tax, 'taxtype', None))


def _get_expense_company_country(request=None, using=None):
    try:
        db = using or getattr(request, 'company_db', None) or 'default'
    except Exception:
        db = using or 'default'
    company = Company.objects.using(db).order_by('id').first()
    return getattr(company, 'country', '') if company else ''


def _is_indian_company(request=None, using=None):
    return get_company_tax_type(using=using or getattr(request, 'company_db', None) or 'default') == 'GST'


def _get_active_company(request):
    company_id = request.session.get('company_id')
    if company_id:
        company = Company.objects.filter(pk=company_id).first()
        if company:
            return company

    company_db = getattr(request, 'company_db', None)
    if company_db and company_db != 'default':
        company = Company.objects.filter(db_name=company_db).first()
        if company:
            return company

    return Company.objects.order_by('id').first()


def _get_expense_currency_context(request, selected_currency_code=''):
    company = _get_active_company(request)
    currencies = []
    if company:
        currencies = list(
            MasterCurrency.objects.filter(company=company, is_active=True).order_by('-is_base', 'code')
        )

    base_currency = next((cur for cur in currencies if cur.is_base), None) or (currencies[0] if currencies else None)
    base_currency_symbol = ((getattr(base_currency, 'symbol', '') or getattr(base_currency, 'code', '') or '₹').strip()) if base_currency else '₹'
    base_currency_code = ((getattr(base_currency, 'code', '') or '').strip().upper()) if company else ''

    currency_symbol_map = {'': base_currency_symbol}
    for currency in currencies:
        code = (currency.code or '').strip().upper()
        if code:
            currency_symbol_map[code] = (currency.symbol or currency.code or base_currency_symbol).strip()

    selected_currency_code = (selected_currency_code or '').strip().upper()
    selected_currency_symbol = currency_symbol_map.get(selected_currency_code, base_currency_symbol)

    return {
        'active_company': company,
        'company_base_currency_symbol': base_currency_symbol,
        'company_base_currency_code': base_currency_code,
        'selected_currency_symbol': selected_currency_symbol,
        'currency_symbol_map_json': json.dumps(currency_symbol_map),
    }


def _get_form_currency_code(form, fallback=''):
    if form is None:
        return (fallback or '').strip().upper()

    try:
        if form.is_bound:
            return str(form.data.get(form.add_prefix('currency')) or fallback or '').strip().upper()
        value = form['currency'].value()
        return str(value or fallback or '').strip().upper()
    except Exception:
        return str(fallback or '').strip().upper()


def _render_expense_form(request, form, formset, title, expense=None, **extra_context):
    selected_currency_code = _get_form_currency_code(form, getattr(expense, 'currency', ''))
    context = {
        'form': form,
        'formset': formset,
        'title': title,
        'expense': expense,
        'is_indian_company': _is_indian_company(request),
    }
    context.update(_get_expense_currency_context(request, selected_currency_code))
    context.update(extra_context)
    return render(request, 'expenses/expense_form.html', context)

@login_required
def expense_list(request):
    # Permission: require view access to Purchase Expenses
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_purchase_expenses(request.user)):
            messages.error(request, 'You do not have permission to view expenses.')
            return redirect_with_company('index')
    except Exception:
        messages.error(request, 'You do not have permission to view expenses.')
        return redirect_with_company('index')
    
    # Only show active (non-deleted) expenses
    qs = Expense.objects.filter(status=True).order_by('-date')
    paginator = Paginator(qs, 10)  # 10 items per page
    page = request.GET.get('page')
    expenses = paginator.get_page(page)
    
    context = {
        'expenses': expenses,
        'can_view_purchase_expenses': can_view_purchase_expenses(request.user),
        'can_create_purchase_expenses': can_create_purchase_expenses(request.user),
        'can_edit_purchase_expenses': can_edit_purchase_expenses(request.user),
        'can_delete_purchase_expenses': can_delete_purchase_expenses(request.user),
    }
    
    return render(request, 'expenses/expense_list.html', context)

@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    try:
        from customer.models import Customer
        if expense.customer:
            try:
                customer = Customer.objects.get(pk=expense.customer)
                customer_display = str(customer)
            except Customer.DoesNotExist:
                customer_display = expense.customer
        else:
            customer_display = "-"
    except ImportError:
        customer_display = expense.customer or "-"
    # Build a display label for each expense line's tax so combined GST can be shown
    # Attach the computed display string as an attribute on each line object
    lines = list(expense.lines.all())
    # Compute display labels and amounts for each line (so UI shows combined GST amounts)
    display_subtotal = 0.0
    display_tax_total = 0.0
    try:
        is_tax_inclusive = expense.amount_is == 'inclusive'
        for line in lines:
            if not line.tax:
                line.tax_display = '-'
                line.tax_amount_display = 0.0
                base_amount = float(line.amount or 0)
                line.total_amount_display = base_amount
                display_subtotal += base_amount
                continue

            tax = line.tax
            total_amount = float(line.amount or 0)
            
            # Handle both IGST and CGST+SGST cases for tax inclusive/exclusive
            tax_rate = float(tax.rate or 0)
            
            # If CGST or SGST, try to find counterpart with same rate and treat as combined GST
            tax_type_code = _get_tax_type_code(tax)
            counterpart = None
            if tax_type_code in ('CGST', 'SGST'):
                counterpart_type = 'SGST' if tax_type_code == 'CGST' else 'CGST'
                counterpart = Tax.objects.filter(taxtype__name__iexact=counterpart_type, rate=tax.rate).first()
                if counterpart:
                    tax_rate = tax_rate * 2  # Combined rate for CGST+SGST
                    combined_display = f"GST{int(tax_rate) if tax_rate.is_integer() else tax_rate} ({tax_rate:.2f}%)"
                    line.tax_display = combined_display

            else:
                # IGST or other tax types
                line.tax_display = f"{tax.taxname} ({tax.rate}%)"
            
            # Calculate amounts based on tax inclusive/exclusive setting
            if is_tax_inclusive:
                # For tax inclusive: extract base and tax from total
                base_amount = total_amount / (1 + (tax_rate / 100.0))
                tax_amount = total_amount - base_amount
            else:
                # For tax exclusive: compute tax and add to base
                base_amount = total_amount
                tax_amount = base_amount * (tax_rate / 100.0)
            
            line.tax_amount_display = tax_amount
            line.total_amount_display = total_amount if is_tax_inclusive else (base_amount + tax_amount)
            display_subtotal += base_amount
            display_tax_total += tax_amount
            
            if tax_type_code in ('CGST', 'SGST') and counterpart:
                # We've already computed amounts for this line (either IGST or combined GST)
                # Skip the fallback re-computation below to avoid double-counting
                continue  # Skip counterpart processing since we handled combined rate
            else:
                continue

            # Fallback: single tax rate applies
            try:
                tax_rate = float(tax.rate)
            except Exception:
                tax_rate = 0.0
                
            line.tax_display = f"{tax.taxname} ({tax.rate}%)"
            
            if is_tax_inclusive:
                # For tax inclusive: extract base and tax from total
                base_amount = total_amount / (1 + (tax_rate / 100.0))
                tax_amount = total_amount - base_amount
            else:
                # For tax exclusive: compute tax and add to base
                base_amount = total_amount
                tax_amount = base_amount * (tax_rate / 100.0)
            
            line.tax_amount_display = tax_amount
            line.total_amount_display = total_amount if is_tax_inclusive else (base_amount + tax_amount)
            display_subtotal += base_amount
            display_tax_total += tax_amount
    except Exception:
        # In case Tax model not available or other error, fall back
        display_subtotal = 0.0
        display_tax_total = 0.0
        for line in lines:
            total_amount = float(getattr(line, 'amount', 0) or 0)
            if line.tax:
                try:
                    tax_rate = float(line.tax.rate)
                    if is_tax_inclusive:
                        base_amount = total_amount / (1 + (tax_rate / 100.0))
                        tax_amount = total_amount - base_amount
                    else:
                        base_amount = total_amount
                        tax_amount = base_amount * (tax_rate / 100.0)
                except Exception:
                    base_amount = total_amount
                    tax_amount = 0.0
            else:
                base_amount = total_amount
                tax_amount = 0.0
            display_subtotal += base_amount
            display_tax_total += tax_amount
            line.tax_display = (f"{line.tax.taxname} ({line.tax.rate}%)" if line.tax else '-')
            line.tax_amount_display = tax_amount
            line.total_amount_display = total_amount if is_tax_inclusive else (base_amount + tax_amount)

    display_total = display_subtotal + display_tax_total

    return render(request, 'expenses/expense_detail.html', {
        'expense': expense,
        'customer_display': customer_display,
        'lines': lines,
        'display_subtotal': display_subtotal,
        'display_tax_total': display_tax_total,
        'display_total': display_total,
        'company_base_currency_code': _get_expense_currency_context(request).get('company_base_currency_code'),
        'company_base_currency_symbol': _get_expense_currency_context(request).get('company_base_currency_symbol'),
    })

@login_required
def expense_create(request):
    if request.method == 'POST':
        # ✅ CHECK PERIOD LOCK BEFORE CREATING EXPENSE
        from datetime import datetime
        from django.core.exceptions import PermissionDenied
        from system_settings.validators import PeriodLockEnforcer
        
        db = getattr(request, 'company_db', 'default')
        date_str = request.POST.get('date')
        if date_str:
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date() if isinstance(date_str, str) else date_str
            except:
                expense_date = None
            
            if expense_date:
                try:
                    PeriodLockEnforcer.check_can_edit(expense_date, request.user, db=db, transaction_type='expense')
                except PermissionDenied as e:
                    company = _get_active_company(request)
                    form = ExpenseForm(company=company)
                    formset = ExpenseLineFormSet(prefix='lines')
                    return _render_expense_form(
                        request,
                        form,
                        formset,
                        'Create Expense',
                        error_message=str(e),
                        show_error_modal=True,
                    )
        
        company = _get_active_company(request)
        form = ExpenseForm(request.POST, company=company)
        formset = ExpenseLineFormSet(request.POST, prefix='lines')
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Save the expense first
                    expense = form.save(commit=False)
                    expense.created_by = request.user
                    # --- CURRENCY FX HANDLING ---
                    cur_code = (expense.currency or 'INR').strip().upper()
                    from currencies.models import Currency as MasterCurrency
                    doc_cur = MasterCurrency.objects.filter(company=company, code=cur_code, is_active=True).first()
                    
                    raw_rate = request.POST.get('fx_rate_to_base')
                    if raw_rate:
                        try:
                            rate = Decimal(str(raw_rate))
                        except:
                            rate = get_effective_rate_to_base(doc_cur, expense.date)
                    else:
                        rate = get_effective_rate_to_base(doc_cur, expense.date)
                        
                    expense.fx_rate_to_base = rate
                    expense.fx_rate_date = expense.date 
                    expense.save()


                    # Save the expense lines
                    formset.instance = expense
                    formset.save()
                    
                    from currencies.services import refresh_document_total_base
                    refresh_document_total_base(expense)
                    # -----------------------------
                    
                    # Save the expense lines
                    formset.instance = expense

                    # Attempt to create a corresponding journal entry so taxes show in COA
                    try:
                        # Generate JV number (re-use logic similar to journal.create)
                        last_entry = JournalEntry.objects.order_by('-entry_number').first()
                        if last_entry:
                            try:
                                last_num = int(last_entry.entry_number.split('-')[1])
                                entry_number = f'JV-{str(last_num + 1).zfill(5)}'
                            except Exception:
                                entry_number = f'JV-{expense.pk:05d}'
                        else:
                            entry_number = f'JV-00001'

                        journal = JournalEntry(
                            entry_number=entry_number,
                            date=expense.date,
                            reference=f'Expense {expense.pk}',
                            narration=(expense.invoice_number or f'Expense #{expense.pk}'),
                            created_by=request.user,
                            updated_by=request.user,
                            status='posted'
                        )
                        journal.save(using=db)

                        total_debit = 0
                        total_credit = 0

                        # For each expense line: debit the expense account for base, debit tax accounts for tax amounts
                        for line in expense.lines.all():
                            # We'll compute base_amount and tax total explicitly. This handles combined CGST+SGST cases
                            base_amount = Decimal('0.00')
                            tax_total = Decimal('0.00')

                            if line.tax:
                                taxtype = _get_tax_type_code(line.tax)
                                # If CGST/SGST pair exists, compute combined rate and split
                                if taxtype in ('CGST', 'SGST'):
                                    counterpart_type = 'SGST' if taxtype == 'CGST' else 'CGST'
                                    counterpart = Tax.objects.filter(taxtype__name__iexact=counterpart_type, rate=line.tax.rate).first()
                                    if counterpart:
                                        combined_rate = (Decimal(str(line.tax.rate)) + Decimal(str(counterpart.rate)))
                                        if expense.amount_is == 'inclusive':
                                            # amount stored includes tax_total (combined)
                                            amt = Decimal(str(line.amount or 0))
                                            base_amount = (amt / (Decimal('1.0') + (combined_rate / Decimal('100')))).quantize(Decimal('0.01'))
                                            tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                        else:
                                            base_amount = Decimal(str(line.amount or 0))
                                            tax_total = (base_amount * (combined_rate / Decimal('100'))).quantize(Decimal('0.01'))
                                    else:
                                        # No counterpart: treat as single tax rate
                                        rate = Decimal(str(line.tax.rate or 0))
                                        if expense.amount_is == 'inclusive':
                                            amt = Decimal(str(line.amount or 0))
                                            base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                                            tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                        else:
                                            base_amount = Decimal(str(line.amount or 0))
                                            tax_total = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                                else:
                                    # IGST or other single tax types
                                    rate = Decimal(str(line.tax.rate or 0))
                                    if expense.amount_is == 'inclusive':
                                        amt = Decimal(str(line.amount or 0))
                                        base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                                        tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                    else:
                                        base_amount = Decimal(str(line.amount or 0))
                                        tax_total = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                            else:
                                # No tax on this line
                                if expense.amount_is == 'inclusive':
                                    base_amount = Decimal(str(line.amount or 0))
                                else:
                                    base_amount = Decimal(str(line.amount or 0))

                            # Create debit to expense account for base_amount (if > 0)
                            if base_amount and base_amount != 0:
                                jl = JournalLine(
                                    journal=journal,
                                    account=line.account,
                                    description=f'Expense #{expense.pk} - {line.account.name}',
                                    debit=scale_amount_for_journal(base_amount, expense),
                                    credit=Decimal('0.00')
                                )
                                jl.save(using=db)
                                total_debit += scale_amount_for_journal(base_amount, expense)

                            # Create tax debits depending on tax type
                            if line.tax and tax_total and tax_total != 0:
                                taxtype = _get_tax_type_code(line.tax)
                                if taxtype == 'IGST':
                                    # Find IGST input account by name heuristic
                                    igst_acc = resolve_tax_account('IGST', direction='input', using=db)
                                    if igst_acc:
                                        jl = JournalLine(
                                            journal=journal,
                                            account=igst_acc,
                                            description=f'Expense #{expense.pk} - IGST',
                                            debit=scale_amount_for_journal(tax_total, expense),
                                            credit=Decimal('0.00')
                                        )
                                        jl.save(using=db)
                                        total_debit += scale_amount_for_journal(tax_total, expense)
                                elif taxtype in ('CGST', 'SGST'):
                                    # For GST split, try to find both CGST and SGST accounts and split tax_total equally
                                    cgst_acc = resolve_tax_account('CGST', direction='input', using=db)
                                    sgst_acc = resolve_tax_account('SGST', direction='input', using=db)
                                    if cgst_acc and sgst_acc:
                                        half = (tax_total / Decimal('2')).quantize(Decimal('0.01'))
                                        jl = JournalLine(journal=journal, account=cgst_acc, description=f'Expense #{expense.pk} - CGST', debit=scale_amount_for_journal(half, expense), credit=Decimal('0.00'))
                                        jl.save(using=db)
                                        jl2 = JournalLine(journal=journal, account=sgst_acc, description=f'Expense #{expense.pk} - SGST', debit=scale_amount_for_journal(tax_total - half, expense), credit=Decimal('0.00'))
                                        jl2.save(using=db)
                                        total_debit += scale_amount_for_journal(tax_total, expense)
                                    else:
                                        # Fallback: find any 'input' account
                                        input_acc = resolve_tax_account(taxtype, direction='input', using=db)
                                        if input_acc:
                                            jl = JournalLine(journal=journal, account=input_acc, description=f'Expense #{expense.pk} - Tax', debit=scale_amount_for_journal(tax_total, expense), credit=Decimal('0.00'))
                                            jl.save(using=db)
                                            total_debit += scale_amount_for_journal(tax_total, expense)
                                else:
                                    # Non-GST company tax types post as a single input tax line.
                                    vat_acc = resolve_tax_account(None, direction='input', using=db)
                                    if vat_acc:
                                        jl = JournalLine(
                                            journal=journal,
                                            account=vat_acc,
                                            description=f'Expense #{expense.pk} - {vat_acc.name}',
                                            debit=scale_amount_for_journal(tax_total, expense),
                                            credit=Decimal('0.00')
                                        )
                                        jl.save(using=db)
                                        total_debit += scale_amount_for_journal(tax_total, expense)

                        # Credit the paid_through account for the total (sum of debits)
                        paid_acc = expense.paid_through
                        if total_debit and paid_acc:
                            jl_credit = JournalLine(journal=journal, account=paid_acc, description=f'Payment for expense {expense.pk}', debit=Decimal('0.00'), credit=total_debit)
                            jl_credit.save(using=db)
                            total_credit += total_debit

                        # Recalculate journal totals and save
                        journal.total_debit = total_debit
                        journal.total_credit = total_credit
                        journal.save(using=db)
                    except Exception as je:
                        # Log the exception but don't abort expense save
                        messages.warning(request, f'Expense saved but journal posting failed: {je}')
                    
                    messages.success(request, 'Expense recorded successfully.')
                    return redirect_with_company('expenses:expense_detail', pk=expense.pk)
            except Exception as e:
                messages.error(request, f'Error saving expense: {str(e)}')
    else:
        company = _get_active_company(request)
        currency_context = _get_expense_currency_context(request)
        default_currency_code = currency_context.get('company_base_currency_code') or ''
        form = ExpenseForm(initial={'currency': default_currency_code}, company=company)
        formset = ExpenseLineFormSet(prefix='lines')
    
    return _render_expense_form(request, form, formset, 'Record Expense')

@login_required
def expense_edit(request, pk):
    # Get the expense object or return 404 if not found
    expense = get_object_or_404(Expense, pk=pk)
    
    # Create a formset for expense lines with no extra blank forms
    # This formset allows editing and deleting existing lines
    EditExpenseLineFormSet = inlineformset_factory(Expense, ExpenseLine, 
                                                 form=ExpenseLineForm, 
                                                 extra=0,  # No extra empty forms
                                                 can_delete=True)  # Allow deleting lines
    
    if request.method == 'POST':
        # ✅ CHECK PERIOD LOCK BEFORE EDITING EXPENSE
        from datetime import datetime
        from django.core.exceptions import PermissionDenied
        from system_settings.validators import PeriodLockEnforcer
        
        db = getattr(request, 'company_db', 'default')
        date_str = request.POST.get('date') or expense.date
        if date_str:
            try:
                expense_date = datetime.strptime(str(date_str), '%Y-%m-%d').date() if isinstance(date_str, str) else date_str
            except:
                expense_date = None
            
            if expense_date:
                try:
                    PeriodLockEnforcer.check_can_edit(expense_date, request.user, db=db, transaction_type='expense')
                except PermissionDenied as e:
                    company = _get_active_company(request)
                    form = ExpenseForm(instance=expense, company=company)
                    formset = EditExpenseLineFormSet(prefix='lines')
                    return _render_expense_form(
                        request,
                        form,
                        formset,
                        'Edit Expense',
                        expense=expense,
                        error_message=str(e),
                        show_error_modal=True,
                    )
        
        # Initialize forms with submitted data
        company = _get_active_company(request)
        form = ExpenseForm(request.POST, instance=expense, company=company)
        formset = EditExpenseLineFormSet(request.POST, prefix='lines', instance=expense)
        
        if form.is_valid() and formset.is_valid():
            try:
                # Save both the expense and its lines in a transaction
                with transaction.atomic():
                    expense = form.save(commit=False)
                    # --- CURRENCY FX HANDLING ---
                    cur_code = (expense.currency or 'INR').strip().upper()
                    from currencies.models import Currency as MasterCurrency
                    doc_cur = MasterCurrency.objects.filter(company=company, code=cur_code, is_active=True).first()
                    
                    raw_rate = request.POST.get('fx_rate_to_base')
                    if raw_rate:
                        try:
                            rate = Decimal(str(raw_rate))
                        except:
                            rate = get_effective_rate_to_base(doc_cur, expense.date)
                    else:
                        rate = get_effective_rate_to_base(doc_cur, expense.date)
                        
                    expense.fx_rate_to_base = rate
                    expense.fx_rate_date = expense.date 
                    expense.save()
                    
                    from currencies.services import refresh_document_total_base
                    refresh_document_total_base(expense)
                    # -----------------------------
                    formset.save()
                    
                    
                    # by adarshInstead of deleting existing journal entries, create a reversal
                    # journal for the most recent non-reversal entry (if any), then
                    # proceed to post the updated journal. This preserves audit trail.
                    old_entry = JournalEntry.objects.filter(reference=f'Expense {expense.pk}').exclude(narration__startswith='Reversal of').prefetch_related('lines').order_by('-id').first()
                    if old_entry:
                        reversed_exists = JournalEntry.objects.filter(narration__startswith=f"Reversal of {old_entry.entry_number}").exists()
                        if not reversed_exists:
                            # Generate next JV- number
                            last_entry = JournalEntry.objects.order_by('-id').first()
                            if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JV-'):
                                try:
                                    last_num = int(last_entry.entry_number.split('-')[1])
                                except Exception:
                                    last_num = 0
                            else:
                                last_num = 0
                            next_num = last_num + 1
                            rev_entry_number = f"JV-{str(next_num).zfill(5)}"

                            with transaction.atomic():
                                rev_je = JournalEntry.objects.using(db).create(
                                    entry_number=rev_entry_number,
                                    date=old_entry.date,
                                    reference=old_entry.reference,
                                    narration=f"Reversal of {old_entry.entry_number}",
                                    total_debit=old_entry.total_credit,
                                    total_credit=old_entry.total_debit,
                                    status='posted',
                                    created_by=request.user,
                                    updated_by=request.user
                                )
                                for line in old_entry.lines.all():
                                    JournalLine.objects.using(db).create(
                                        journal=rev_je,
                                        account=line.account,
                                        description=(f"Reversal: {line.description}" if line.description else f"Reversal of line {line.id}"),
                                        debit=line.credit,
                                        credit=line.debit,
                                        sequence=line.sequence,
                                        status=line.status
                                    )
                    
                    # Use by adarshthe most recently created JournalEntry (order by id) to determine next JV number
                    last_entry = JournalEntry.objects.filter(entry_number__startswith='JV-').order_by('-id').first()
                    if last_entry:
                        try:
                            last_num = int(last_entry.entry_number.split('-')[1])
                            entry_number = f'JV-{str(last_num + 1).zfill(5)}'
                        except Exception:
                            entry_number = f'JV-{expense.pk:05d}'
                    else:
                        entry_number = f'JV-00001'

                    journal = JournalEntry(
                        entry_number=entry_number,
                        date=expense.date,
                        reference=f'Expense {expense.pk}',
                        narration=(expense.invoice_number or f'Expense #{expense.pk}'),
                        created_by=request.user,
                        updated_by=request.user,
                        status='posted'
                    )
                    journal.save(using=db)

                    total_debit = 0
                    total_credit = 0

                    # For each expense line: debit the expense account for base, debit tax accounts for tax amounts
                    for line in expense.lines.all():
                        # We'll compute base_amount and tax total explicitly. This handles combined CGST+SGST cases
                        base_amount = Decimal('0.00')
                        tax_total = Decimal('0.00')

                        if line.tax:
                            taxtype = _get_tax_type_code(line.tax)
                            # If CGST/SGST pair exists, compute combined rate and split
                            if taxtype in ('CGST', 'SGST'):
                                counterpart_type = 'SGST' if taxtype == 'CGST' else 'CGST'
                                counterpart = Tax.objects.filter(taxtype__name__iexact=counterpart_type, rate=line.tax.rate).first()
                                if counterpart:
                                    combined_rate = (Decimal(str(line.tax.rate)) + Decimal(str(counterpart.rate)))
                                    if expense.amount_is == 'inclusive':
                                        # amount stored includes tax_total (combined)
                                        amt = Decimal(str(line.amount or 0))
                                        base_amount = (amt / (Decimal('1.0') + (combined_rate / Decimal('100')))).quantize(Decimal('0.01'))
                                        tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                    else:
                                        base_amount = Decimal(str(line.amount or 0))
                                        tax_total = (base_amount * (combined_rate / Decimal('100'))).quantize(Decimal('0.01'))
                                else:
                                    # No counterpart: treat as single tax rate
                                    rate = Decimal(str(line.tax.rate or 0))
                                    if expense.amount_is == 'inclusive':
                                        amt = Decimal(str(line.amount or 0))
                                        base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                                        tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                    else:
                                        base_amount = Decimal(str(line.amount or 0))
                                        tax_total = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                            else:
                                # IGST or other single tax types
                                rate = Decimal(str(line.tax.rate or 0))
                                if expense.amount_is == 'inclusive':
                                    amt = Decimal(str(line.amount or 0))
                                    base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                                    tax_total = (amt - base_amount).quantize(Decimal('0.01'))
                                else:
                                    base_amount = Decimal(str(line.amount or 0))
                                    tax_total = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
                        else:
                            # No tax on this line
                            if expense.amount_is == 'inclusive':
                                base_amount = Decimal(str(line.amount or 0))
                            else:
                                base_amount = Decimal(str(line.amount or 0))

                        # Create debit to expense account for base_amount (if > 0)
                        if base_amount and base_amount != 0:
                            acct_name = getattr(line.account, 'name', str(line.account)) if line.account else 'Expense Account'
                            jl = JournalLine(
                                journal=journal,
                                account=line.account,
                                description=f'Expense #{expense.pk} - {acct_name}',
                                debit=scale_amount_for_journal(base_amount, expense),
                                credit=Decimal('0.00')
                            )
                            jl.save(using=db)
                            total_debit += scale_amount_for_journal(base_amount, expense)

                        # Create tax debits depending on tax type
                        if line.tax and tax_total and tax_total != 0:
                            taxtype = _get_tax_type_code(line.tax)
                            if taxtype == 'IGST':
                                # Find IGST input account by name heuristic
                                igst_acc = resolve_tax_account('IGST', direction='input', using=db)
                                if igst_acc:
                                    jl = JournalLine(
                                        journal=journal,
                                        account=igst_acc,
                                        description=f'Expense #{expense.pk} - IGST {line.tax.rate}%',
                                        debit=scale_amount_for_journal(tax_total, expense),
                                        credit=Decimal('0.00')
                                    )
                                    jl.save(using=db)
                                    total_debit += scale_amount_for_journal(tax_total, expense)
                            elif taxtype in ('CGST', 'SGST'):
                                # For GST split, try to find both CGST and SGST accounts and split tax_total equally
                                cgst_acc = resolve_tax_account('CGST', direction='input', using=db)
                                sgst_acc = resolve_tax_account('SGST', direction='input', using=db)
                                if cgst_acc and sgst_acc:
                                    half = (tax_total / Decimal('2')).quantize(Decimal('0.01'))
                                    jl = JournalLine(journal=journal, account=cgst_acc, description=f'Expense #{expense.pk} - CGST {line.tax.rate}% (split)', debit=scale_amount_for_journal(half, expense), credit=Decimal('0.00'))
                                    jl.save(using=db)
                                    jl2 = JournalLine(journal=journal, account=sgst_acc, description=f'Expense #{expense.pk} - SGST {line.tax.rate}% (split)', debit=scale_amount_for_journal(tax_total - half, expense), credit=Decimal('0.00'))
                                    jl2.save(using=db)
                                    total_debit += scale_amount_for_journal(tax_total, expense)
                                else:
                                    # Fallback: find any 'input' account
                                    input_acc = resolve_tax_account(taxtype, direction='input', using=db)
                                    if input_acc:
                                        jl = JournalLine(journal=journal, account=input_acc, description=f'Expense #{expense.pk} - Tax {line.tax.rate}%', debit=scale_amount_for_journal(tax_total, expense), credit=Decimal('0.00'))
                                        jl.save(using=db)
                                        total_debit += scale_amount_for_journal(tax_total, expense)
                            else:
                                # Non-GST company tax types post as a single input tax line.
                                vat_acc = resolve_tax_account(None, direction='input', using=db)
                                if vat_acc:
                                    jl = JournalLine(
                                        journal=journal,
                                        account=vat_acc,
                                        description=f'Expense #{expense.pk} - {vat_acc.name} {line.tax.rate}%',
                                        debit=scale_amount_for_journal(tax_total, expense),
                                        credit=Decimal('0.00')
                                    )
                                    jl.save(using=db)
                                    total_debit += scale_amount_for_journal(tax_total, expense)

                    # Credit the paid_through account for the total (sum of debits)
                    paid_acc = expense.paid_through
                    if total_debit and paid_acc:
                        jl_credit = JournalLine(journal=journal, account=paid_acc, description=f'Payment for expense {expense.pk}', debit=Decimal('0.00'), credit=total_debit)
                        jl_credit.save(using=db)
                        total_credit += total_debit

                    # Recalculate journal totals and save
                    journal.total_debit = total_debit
                    journal.total_credit = total_credit
                    journal.save(using=db)

                    messages.success(request, 'Expense and journal entries updated successfully.')
                    return redirect_with_company('expenses:expense_detail', pk=expense.pk)
            except Exception as e:
                # Log full traceback for debugging and show modal to user
                logger.error(f'Error updating expense: {e}', exc_info=True)
                # Render form again with an error modal so user sees the failure
                return _render_expense_form(
                    request,
                    form,
                    formset,
                    f'Edit Expense #{expense.pk}',
                    expense=expense,
                    error_message=str(e),
                    show_error_modal=True,
                )
    else:
        # Initialize forms with existing data for GET request
        company = _get_active_company(request)
        form = ExpenseForm(instance=expense, company=company)
        formset = EditExpenseLineFormSet(prefix='lines', instance=expense)
    
    return _render_expense_form(request, form, formset, f'Edit Expense #{expense.pk}', expense=expense)

@login_required
def expense_delete(request, pk):
    # Get the expense object or return 404 if not found
    expense = get_object_or_404(Expense, pk=pk)
    
    # Only process DELETE operations that come through POST
    if request.method == 'POST':
        # ✅ CHECK PERIOD LOCK BEFORE DELETING EXPENSE
        from django.core.exceptions import PermissionDenied
        from system_settings.validators import PeriodLockEnforcer
        
        db = getattr(request, 'company_db', 'default')
        try:
            PeriodLockEnforcer.check_can_edit(expense.date, request.user, db=db, transaction_type='expense')
        except PermissionDenied as e:
            # Return JSON error for AJAX requests, render template for regular requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            else:
                company = _get_active_company(request)
                form = ExpenseForm(company=company)
                formset = EditExpenseLineFormSet(prefix='lines')
                return _render_expense_form(
                    request,
                    form,
                    formset,
                    'Delete Expense',
                    expense=expense,
                    error_message=str(e),
                    show_error_modal=True,
                )
        
        try:
            with transaction.atomic():
                # First, delete associated journal entries and their lines
                for journal in JournalEntry.objects.filter(reference=f'Expense {expense.pk}'):
                    # Delete all lines in this journal entry first
                    JournalLine.objects.filter(journal=journal).delete()
                    # Delete the journal entry
                    journal.delete()
                
                # Mark the expense lines as inactive
                ExpenseLine.objects.filter(expense=expense).update(status=False)
                
                # Mark the expense as inactive
                expense.status = False
                expense.save(update_fields=['status'])

            # Return JSON for AJAX requests, redirect for regular requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Expense and related entries deleted successfully.'
                })
                
            messages.success(request, 'Expense and related entries deleted successfully.')
        except Exception as e:
            error_msg = f'Error deleting expense: {str(e)}'
            # Return JSON for AJAX requests, redirect for regular requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            
            messages.error(request, error_msg)
        
        # Redirect to list view after deletion (successful or failed) - only for non-AJAX requests
        return redirect_with_company('expenses:expense_list')
        
    # If not POST, redirect to detail view (prevents direct GET access)
    return redirect_with_company('expenses:expense_detail', pk=pk)

@login_required
def expense_journal(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    db = getattr(request, 'company_db', 'default')
    lines = expense.lines.all()
    # Build display rows separating base (expense) amounts and input tax if present
    display_rows = []
    total_base = Decimal('0.00')
    total_tax = Decimal('0.00')

    for line in lines:
        base_amount = Decimal('0.00')
        tax_amount = Decimal('0.00')
        is_combined = False

        if line.tax:
            taxtype = _get_tax_type_code(line.tax)
            if taxtype in ('CGST', 'SGST'):
                counterpart_type = 'SGST' if taxtype == 'CGST' else 'CGST'
                counterpart = Tax.objects.filter(taxtype__name__iexact=counterpart_type, rate=line.tax.rate).first()
                if counterpart:
                    is_combined = True
                    combined_rate = (Decimal(str(line.tax.rate)) + Decimal(str(counterpart.rate)))
                    if expense.amount_is == 'inclusive':
                        amt = Decimal(str(line.amount or 0))
                        base_amount = (amt / (Decimal('1.0') + (combined_rate / Decimal('100')))).quantize(Decimal('0.01'))
                        tax_amount = (amt - base_amount).quantize(Decimal('0.01'))
                    else:
                        base_amount = Decimal(str(line.amount or 0))
                        tax_amount = (base_amount * (combined_rate / Decimal('100'))).quantize(Decimal('0.01'))
                else:
                    rate = Decimal(str(line.tax.rate or 0))
                    if expense.amount_is == 'inclusive':
                        amt = Decimal(str(line.amount or 0))
                        base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                        tax_amount = (amt - base_amount).quantize(Decimal('0.01'))
                    else:
                        base_amount = Decimal(str(line.amount or 0))
                        tax_amount = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
            else:
                # IGST or other single tax types
                rate = Decimal(str(line.tax.rate or 0))
                if expense.amount_is == 'inclusive':
                    amt = Decimal(str(line.amount or 0))
                    base_amount = (amt / (Decimal('1.0') + (rate / Decimal('100')))).quantize(Decimal('0.01'))
                    tax_amount = (amt - base_amount).quantize(Decimal('0.01'))
                else:
                    base_amount = Decimal(str(line.amount or 0))
                    tax_amount = (base_amount * (rate / Decimal('100'))).quantize(Decimal('0.01'))
        else:
            base_amount = Decimal(str(line.amount or 0))

        total_base += base_amount
        total_tax += tax_amount

        # Add expense (base) row for this line
        display_rows.append({
            'account_name': getattr(line.account, 'name', str(line.account)),
            'debit': base_amount,
            'credit': Decimal('0.00')
        })

        # Add tax rows: split into CGST/SGST if combined, otherwise use IGST/input account
        if tax_amount and tax_amount != Decimal('0.00'):
            if is_combined:
                half = (tax_amount / Decimal('2')).quantize(Decimal('0.01'))
                cgst_acc = resolve_tax_account('CGST', direction='input', using=db)
                sgst_acc = resolve_tax_account('SGST', direction='input', using=db)
                cgst_name = cgst_acc.name if cgst_acc else 'Input Tax CGST'
                sgst_name = sgst_acc.name if sgst_acc else 'Input Tax SGST'
                display_rows.append({'account_name': cgst_name, 'debit': half, 'credit': Decimal('0.00')})
                display_rows.append({'account_name': sgst_name, 'debit': tax_amount - half, 'credit': Decimal('0.00')})
            else:
                # Check if this is an India company
                is_india = _is_indian_company(request=request, using=db)
                if is_india and taxtype == 'IGST':
                    acc = resolve_tax_account('IGST', direction='input', using=db)
                    acc_name = acc.name if acc else 'Input Tax IGST'
                elif not is_india:
                    vat_acc = resolve_tax_account(None, direction='input', using=db)
                    acc_name = vat_acc.name if vat_acc else 'Input Tax'
                else:
                    acc = resolve_tax_account(taxtype, direction='input', using=db)
                    acc_name = acc.name if acc else 'Input Tax (GST)'
                display_rows.append({'account_name': acc_name, 'debit': tax_amount, 'credit': Decimal('0.00')})

    # Paid through account as a single credit for the total (base + tax)
    display_total = (total_base + total_tax).quantize(Decimal('0.01'))
    display_rows.append({
        'account_name': getattr(expense.paid_through, 'name', str(expense.paid_through)),
        'debit': Decimal('0.00'),
        'credit': display_total
    })

    return render(request, 'expenses/expense_journal.html', {
        'expense': expense,
        'display_rows': display_rows,
        'display_base_total': total_base.quantize(Decimal('0.01')),
        'display_tax_total': total_tax.quantize(Decimal('0.01')),
        'display_total': display_total,
        'company_base_currency_code': _get_expense_currency_context(request).get('company_base_currency_code'),
        'company_base_currency_symbol': _get_expense_currency_context(request).get('company_base_currency_symbol'),
    })


@login_required
def currency_create(request):
    """AJAX-friendly view to create a shared company currency from the expense form modal."""
    company = _get_active_company(request)

    if not company:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'No active company found.'}, status=400)
        return render(request, 'expenses/currency_modal.html', {})

    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip().upper()[:3]
        symbol = (request.POST.get('symbol') or '').strip()[:8]
        name = (request.POST.get('name') or '').strip()[:80]

        if not code or not name:
            return JsonResponse({'success': False, 'error': 'Code and name are required.'}, status=400)

        if MasterCurrency.objects.filter(company=company, code__iexact=code).exists():
            existing = MasterCurrency.objects.filter(company=company, code__iexact=code).first()
            return JsonResponse({
                'success': False,
                'error': 'Currency already exists.',
                'code': existing.code if existing else code,
                'display': f"{existing.code} - {existing.name}" if existing and existing.name else code,
                'symbol': (getattr(existing, 'symbol', '') or code) if existing else (symbol or code),
            }, status=400)

        try:
            obj = MasterCurrency.objects.create(
                company=company,
                code=code,
                symbol=symbol or code,
                name=name or code,
                decimal_places=2,
                display_format='1,234.56',
                is_base=False,
                is_active=True,
            )
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'Currency already exists.'}, status=400)

        return JsonResponse({
            'success': True,
            'code': obj.code,
            'display': f"{obj.code} - {obj.name}" if obj.name and obj.name.strip().upper() != obj.code else obj.code,
            'symbol': (obj.symbol or obj.code),
        })

    # For GET requests return the modal fragment
    return render(request, 'expenses/currency_modal.html', {})
