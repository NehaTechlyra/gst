from django.shortcuts import render, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from .models import ChartOfAccounts
from .forms import ChartOfAccountsForm
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
from Lyraerp.utils.redirect_utils import get_company_redirect_url
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from journal.models import JournalLine
from sales.models import SalesInvoice
from stock.models import Stock
from Purchase.models import BillItem
from journal.models import JournalEntry
from Purchase.models import Bill
from expenses.models import Expense
from operator import itemgetter
import logging
from decimal import Decimal
import re
from urllib.parse import urlencode
from .permissions import (
    can_view_chart, can_create_chart, can_edit_chart, can_delete_chart,
    can_view_journal,
    can_view_balance_sheet, can_view_profit_loss, can_view_trial_balance, can_view_cash_flow
)
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)


def account_list(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_chart(request.user)):
            messages.error(request, 'You do not have permission to view Chart of Accounts.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view Chart of Accounts.')
        return redirect_with_company('home')

    search_query = request.GET.get('q', '')
    accounts = ChartOfAccounts.objects.filter(active=True, status=True)

    if search_query:
        accounts = accounts.filter(Q(name__icontains=search_query))

    accounts = accounts.order_by('id')
    paginator = Paginator(accounts, 10)
    page_number = request.GET.get('page')
    account_page = paginator.get_page(page_number)

    context = {
        "accounts": account_page,
        "search_query": search_query,
        "can_create": (getattr(request.user, 'is_superuser', False) or can_create_chart(request.user)),
        "can_edit": (getattr(request.user, 'is_superuser', False) or can_edit_chart(request.user)),
        "can_delete": (getattr(request.user, 'is_superuser', False) or can_delete_chart(request.user)),
    }
    return render(request, "accounts_list.html", context)


@login_required
def create_account(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_chart(request.user)):
            messages.error(request, 'You do not have permission to create accounts.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to create accounts.')
        return redirect_with_company('accounts-list')

    if request.method == "POST":
        form = ChartOfAccountsForm(request.POST)
        if form.is_valid():
            new_account = form.save(commit=False)
            new_account.code = generate_code(new_account.parent)
            if not form.cleaned_data.get('search_code'):
                new_account.search_code = new_account.code
            new_account.created_by = request.user
            new_account.save()
            messages.success(request, "Account created successfully.")
            return redirect_with_company('accounts-list')
    else:
        form = ChartOfAccountsForm()

    return render(request, 'create_account.html', {'form': form, 'title': 'Add New Account'})


@login_required
def create_account_tree(request):
    if request.method == "POST":
        form = ChartOfAccountsForm(request.POST)
        if form.is_valid():
            new_account = form.save(commit=False)
            new_account.code = generate_code(new_account.parent)
            if not form.cleaned_data.get('search_code'):
                new_account.search_code = new_account.code
            new_account.created_by = request.user
            new_account.save()
            messages.success(request, "Account created successfully.")
            return redirect_with_company('chart_of_accounts_tree')
    else:
        form = ChartOfAccountsForm()

    return render(request, 'create_account.html', {'form': form, 'title': 'Add New Account'})


def generate_code(parent):
    if parent is None:
        siblings = ChartOfAccounts.objects.filter(parent__isnull=True)
        if not siblings.exists():
            return "1"
        max_code = max(int(acc.code) for acc in siblings if acc.code.isdigit())
        return str(max_code + 1)
    else:
        siblings = ChartOfAccounts.objects.filter(parent=parent)
        parent_code = parent.code

        if len(parent_code) <= 3:
            existing_codes = [acc.code for acc in siblings if acc.code.startswith(parent_code)]
            numbers = [
                int(code[len(parent_code):])
                for code in existing_codes
                if code[len(parent_code):].isdigit()
            ]
            next_num = max(numbers) + 1 if numbers else 1
            return f"{parent_code}{next_num:02d}"
        else:
            existing_codes = [acc.code for acc in siblings if acc.code.startswith(parent_code)]
            numbers = [
                int(code[len(parent_code):])
                for code in existing_codes
                if code[len(parent_code):].isdigit()
            ]
            next_num = max(numbers) + 1 if numbers else 1
            return f"{parent_code}{next_num:02d}"


def get_parents_for_type(request):
    type_code = request.GET.get('type_code', None)
    data = []
    if type_code:
        parents = ChartOfAccounts.objects.filter(
            code__startswith=type_code, is_header=1
        ).order_by('code')
        data = [
            {
                'id': parent.id,
                'name': f"{parent.name} ({parent.search_code})" if parent.search_code else parent.name
            }
            for parent in parents
        ]
    return JsonResponse({'parents': data})


@login_required
def edit_account(request, pk):
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_chart(request.user)):
            messages.error(request, 'You do not have permission to edit accounts.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to edit accounts.')
        return redirect_with_company('accounts-list')

    if request.method == 'POST':
        form = ChartOfAccountsForm(request.POST, instance=account)
        if form.is_valid():
            edited_account = form.save(commit=False)
            parent = form.cleaned_data.get('parent')

            if parent and isinstance(parent, str):
                try:
                    parent = ChartOfAccounts.objects.get(pk=parent)
                except ChartOfAccounts.DoesNotExist:
                    parent = None
            elif parent is None or (hasattr(parent, 'code') and parent.code):
                pass
            else:
                try:
                    parent_id = int(parent)
                    parent = ChartOfAccounts.objects.get(pk=parent_id)
                except Exception:
                    parent = None

            edited_account.parent = parent
            edited_account.code = generate_code(parent)
            edited_account.updated_by = request.user
            edited_account.save()
            messages.success(request, "Account updated successfully.")
            return redirect_with_company('accounts-list')
    else:
        form = ChartOfAccountsForm(instance=account)

    return render(request, 'create_account.html', {'form': form, 'title': 'Edit Account'})


@require_POST
def delete_account(request, pk):
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_chart(request.user)):
            messages.error(request, 'You do not have permission to delete accounts.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to delete accounts.')
        return redirect_with_company('accounts-list')

    account.status = False
    account.save(update_fields=["status"])
    messages.success(request, "Account deleted successfully.")
    return redirect_with_company('accounts-list')


@login_required
def generate_code_ajax(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_chart(request.user)):
            return JsonResponse({'error': 'Permission denied.'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    parent_id = request.GET.get('parent')
    parent = ChartOfAccounts.objects.filter(id=parent_id).first() if parent_id else None
    new_code = generate_code(parent)
    return JsonResponse({'code': new_code})


def get_account_types(request):
    types = ChartOfAccounts.objects.filter(parent__isnull=True, active=True, status=True).order_by('code')
    data = [{'id': t.id, 'code': t.code, 'name': t.name} for t in types]
    return JsonResponse({'types': data})


def _apply_filter_preset(filter_preset):
    """Return (from_date_str, to_date_str) for a given preset key."""
    from datetime import date, timedelta

    if not filter_preset:
        return '', ''

    today = date.today()

    def start_of_week(d):
        return d - timedelta(days=d.weekday())

    def start_of_month(d):
        return d.replace(day=1)

    def start_of_quarter(d):
        q = (d.month - 1) // 3
        first_month = q * 3 + 1
        return d.replace(month=first_month, day=1)

    def start_of_year(d):
        return d.replace(month=1, day=1)

    if filter_preset == 'today':
        return str(today), str(today)
    if filter_preset == 'yesterday':
        y = today - timedelta(days=1)
        return str(y), str(y)
    if filter_preset == 'this_week':
        s = start_of_week(today)
        return str(s), str(today)
    if filter_preset == 'previous_week':
        end = start_of_week(today) - timedelta(days=1)
        start = end - timedelta(days=6)
        return str(start), str(end)
    if filter_preset == 'this_month':
        s = start_of_month(today)
        return str(s), str(today)
    if filter_preset == 'previous_month':
        first_this = start_of_month(today)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return str(first_prev), str(last_prev)
    if filter_preset == 'this_quarter':
        s = start_of_quarter(today)
        return str(s), str(today)
    if filter_preset == 'previous_quarter':
        s = start_of_quarter(today)
        last_day_prev = s - timedelta(days=1)
        start_prev = start_of_quarter(last_day_prev)
        return str(start_prev), str(last_day_prev)
    if filter_preset == 'this_year':
        s = start_of_year(today)
        return str(s), str(today)
    if filter_preset == 'previous_year':
        s = start_of_year(today).replace(year=today.year - 1)
        e = s.replace(month=12, day=31)
        return str(s), str(e)

    return '', ''


@login_required
def create_account_ajax(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_chart(request.user)):
            return JsonResponse({'error': 'Permission denied.'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    name = request.POST.get('name')
    type_code = request.POST.get('type')
    parent_id = request.POST.get('parent')
    description = request.POST.get('description', '')
    is_header = request.POST.get('is_header') in ['1', 'true', 'on']
    active = request.POST.get('active') in ['1', 'true', 'on']

    if not name or not type_code:
        return JsonResponse({'error': 'Name and type are required.'}, status=400)

    parent = ChartOfAccounts.objects.filter(id=parent_id).first() if parent_id else None

    try:
        new_account = ChartOfAccounts(
            name=name,
            type=type_code,
            parent=parent,
            description=description,
            is_header=is_header,
            active=active,
            created_by=request.user
        )
        new_account.code = generate_code(parent)
        if not request.POST.get('search_code'):
            new_account.search_code = new_account.code
        new_account.save()
        return JsonResponse({
            'success': True,
            'id': new_account.id,
            'name': new_account.name,
            'code': new_account.code,
        })
    except Exception as e:
        logger.exception(f"create_account_ajax failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def build_tree(accounts, parent_code, expected_length):
    children = [
        a for a in accounts
        if len(a.code) == expected_length and a.code.startswith(parent_code)
    ]
    tree = []
    for child in children:
        subtree = build_tree(accounts, child.code, expected_length + 2)
        tree.append({
            "id": child.id,
            "code": child.code,
            "name": child.name,
            "description": child.description,
            "children": subtree,
        })
    return tree


def chart_of_accounts_tree(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_chart(request.user)):
            messages.error(request, 'You do not have permission to view Chart of Accounts.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view Chart of Accounts.')
        return redirect_with_company('home')

    accounts = ChartOfAccounts.objects.filter(active=True, status=True).order_by('code')
    superparents = [a for a in accounts if len(a.code) == 1]

    tree = []
    for sp in superparents:
        children_tree = build_tree(accounts, sp.code, 3)
        tree.append({
            "id": sp.id,
            "code": sp.code,
            "name": sp.name,
            "description": sp.description,
            "children": children_tree,
        })

    context = {
        'tree': tree,
        'can_create': (getattr(request.user, 'is_superuser', False) or can_create_chart(request.user)),
        'can_edit': (getattr(request.user, 'is_superuser', False) or can_edit_chart(request.user)),
        'can_delete': (getattr(request.user, 'is_superuser', False) or can_delete_chart(request.user)),
    }
    return render(request, 'treeview.html', context)


@login_required
def account_detail(request, pk):
    account = get_object_or_404(ChartOfAccounts, pk=pk)
    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (
            getattr(request.user, 'is_superuser', False)
            or can_view_chart(request.user)
            or can_view_journal(request.user)
            or has_reports_access
        ):
            messages.error(request, 'You do not have permission to view this account journal.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view this account journal.')
        return redirect_with_company('accounts-list')

    from datetime import datetime
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    filter_preset = request.GET.get('filter_preset', '')
    
    company_db = getattr(request, 'company_db', 'default')
    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)
    
    if selected_fy and not date_from and not date_to and not filter_preset:
        date_from = fy_from_date.strftime('%Y-%m-%d') if fy_from_date else ''
        date_to = fy_to_date.strftime('%Y-%m-%d') if fy_to_date else ''
    elif filter_preset:
        date_from, date_to = _apply_filter_preset(filter_preset)

    journal = []

    try:
        jl_qs = JournalLine.objects.using(company_db).filter(
            account=account,
            journal__status='posted',
            status=True,
        ).select_related('journal').order_by('journal__date', 'id')

        if date_from:
            try:
                jl_qs = jl_qs.filter(
                    journal__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
                )
            except Exception:
                pass

        if date_to:
            try:
                jl_qs = jl_qs.filter(
                    journal__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
                )
            except Exception:
                pass

        all_refs = [jl.journal.reference or '' for jl in jl_qs]
        inv_numbers = set()
        bill_numbers = set()
        payment_numbers = set()
        for ref in all_refs:
            m = re.search(r'\bIN([0-9][0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
            if m:
                inv_numbers.add('IN' + m.group(1))
            m2 = re.search(r'\bBN([0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
            if m2:
                bill_numbers.add('BN' + m2.group(1))
            m3 = re.search(r'Payment\s*#(\d+)', ref, re.IGNORECASE)
            if m3:
                payment_numbers.add(int(m3.group(1)))

        invoice_map = {
            inv.inv_number: inv
            for inv in SalesInvoice.objects.using(company_db).filter(inv_number__in=inv_numbers)
            .select_related('customer')
        } if inv_numbers else {}

        bill_map = {
            bill.bill_number: bill
            for bill in Bill.objects.using(company_db).filter(bill_number__in=bill_numbers)
            .select_related('vendor')
        } if bill_numbers else {}

        from Purchase.models import BillPayment
        from sales.models import InvPayment
        
        bill_payment_map = {
            bp.payment_number: bp
            for bp in BillPayment.objects.using(company_db).filter(payment_number__in=payment_numbers)
            .select_related('vendor')
        } if payment_numbers else {}

        inv_payment_map = {
            ip.payment_number: ip
            for ip in InvPayment.objects.using(company_db).filter(payment_number__in=payment_numbers)
            .select_related('customer')
        } if payment_numbers else {}

        running_balance = 0
        for jl in jl_qs:
            debit_amt = float(jl.debit or 0)
            credit_amt = float(jl.credit or 0)
            running_balance += debit_amt - credit_amt
            amt = float(jl.debit) if jl.debit else float(jl.credit or 0)

            expense_obj = None
            expense_type = None
            ref = (jl.journal.reference or '').strip()
            narration = (jl.journal.narration or '').strip().lower()

            if ref.startswith('Payment'):
                m_pay = re.search(r'Payment\s*#(\d+)', ref, re.IGNORECASE)
                if m_pay:
                    payment_num = int(m_pay.group(1))
                    if 'received from' in narration or 'payment received' in narration:
                        if payment_num in inv_payment_map:
                            expense_obj = inv_payment_map[payment_num]
                            expense_type = 'inv_payment'
                    elif 'payment to vendor' in narration or 'payment to' in narration:
                        if payment_num in bill_payment_map:
                            expense_obj = bill_payment_map[payment_num]
                            expense_type = 'bill_payment'
                    else:
                        if payment_num in bill_payment_map:
                            expense_obj = bill_payment_map[payment_num]
                            expense_type = 'bill_payment'
                        elif payment_num in inv_payment_map:
                            expense_obj = inv_payment_map[payment_num]
                            expense_type = 'inv_payment'

            if ref.startswith('Expense'):
                try:
                    parts = ref.split()
                    if len(parts) >= 2:
                        expense_obj = Expense.objects.using(company_db).filter(pk=int(parts[1]), status=True).first()
                        if expense_obj:
                            expense_type = 'expense'
                except Exception:
                    pass

            if not expense_obj and ref:
                inv = invoice_map.get(ref)
                if inv:
                    expense_obj = inv
                    expense_type = 'invoice'

            if not expense_obj and ref:
                bill = bill_map.get(ref)
                if bill:
                    expense_obj = bill
                    expense_type = 'bill'

            if not expense_obj:
                expense_obj = jl.journal
                expense_type = 'journal'

            party_name = None
            party_type = None
            party_pk = None

            try:
                if expense_type == 'invoice' and getattr(expense_obj, 'customer', None):
                    party_name = str(expense_obj.customer)
                    party_type = 'customer'
                    party_pk = expense_obj.customer.pk
                elif expense_type == 'bill' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                    party_type = 'vendor'
                    party_pk = expense_obj.vendor.pk
                elif expense_type == 'expense' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                    party_type = 'vendor'
                    party_pk = expense_obj.vendor.pk
                elif expense_type == 'bill_payment' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                    party_type = 'vendor'
                    party_pk = expense_obj.vendor.pk
                elif expense_type == 'inv_payment' and getattr(expense_obj, 'customer', None):
                    party_name = str(expense_obj.customer)
                    party_type = 'customer'
                    party_pk = expense_obj.customer.pk
                elif expense_type == 'journal' and ref and ('reversal' in ref.lower() or 'cancel' in ref.lower()):
                    bill_match = re.search(r'\b(BN[0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
                    if bill_match:
                        bill_ref = bill_match.group(1)
                        if bill_ref in bill_map:
                            original_bill = bill_map[bill_ref]
                            if original_bill.vendor:
                                party_name = str(original_bill.vendor)
                                party_type = 'vendor'
                                party_pk = original_bill.vendor.pk
                    if not party_name:
                        inv_match = re.search(r'\b(IN[0-9][0-9A-Za-z\-_/]*)\b', ref, re.IGNORECASE)
                        if inv_match:
                            inv_ref = inv_match.group(1)
                            if inv_ref in invoice_map:
                                original_inv = invoice_map[inv_ref]
                                if original_inv.customer:
                                    party_name = str(original_inv.customer)
                                    party_type = 'customer'
                                    party_pk = original_inv.customer.pk
                    if not party_name:
                        pay_match = re.search(r'(?:PAY|Payment)[- ]?(\d+)', ref, re.IGNORECASE)
                        if pay_match:
                            payment_num = int(pay_match.group(1))
                            if payment_num in bill_payment_map:
                                payment = bill_payment_map[payment_num]
                                if payment.vendor:
                                    party_name = str(payment.vendor)
                                    party_type = 'vendor'
                                    party_pk = payment.vendor.pk
                            elif payment_num in inv_payment_map:
                                payment = inv_payment_map[payment_num]
                                if payment.customer:
                                    party_name = str(payment.customer)
                                    party_type = 'customer'
                                    party_pk = payment.customer.pk
            except Exception:
                pass

            party_url = None
            try:
                if party_type and party_pk:
                    from Lyraerp.utils.redirect_utils import get_company_code
                    company_code = get_company_code(request)
                    party_url = f"/{company_code}/chart_of_accounts/party/{party_type}/{party_pk}/"
                    if selected_fy:
                        party_url = f"{party_url}?fy_id={selected_fy.id}"
            except Exception:
                party_url = None

            journal.append({
                'date': jl.journal.date,
                'expense': expense_obj,
                'expense_type': expense_type,
                'journal_pk': jl.journal.pk,
                'account': jl.account.name,
                'amount': amt,
                'debit': debit_amt,
                'credit': credit_amt,
                'running_balance': abs(running_balance),
                'running_balance_display': (
                    f"{abs(running_balance):.2f} {'Dr' if running_balance >= 0 else 'Cr'}"
                ),
                'party_name': party_name,
                'party_type': party_type,
                'party_pk': party_pk,
                'party_url': party_url,
            })

    except Exception:
        logger.exception(f"account_detail journal query failed for pk={pk}")

    try:
        journal = sorted(journal, key=itemgetter('date'))
    except Exception:
        pass

    paginator = Paginator(journal, 10)
    journal_page = paginator.get_page(request.GET.get('page'))

    company_code = None
    try:
        company_code = request.resolver_match.kwargs.get('company_code')
    except Exception:
        pass
    if not company_code:
        try:
            parts = [p for p in (request.path or '').split('/') if p]
            company_code = parts[0] if parts else None
        except Exception:
            pass

    query_data = {
        k: v for k, v in {
            'date_from': date_from,
            'date_to': date_to,
            'filter_preset': filter_preset,
        }.items() if v
    }
    if company_code:
        base_download_url = reverse(
            'account_ledger_download_pdf',
            kwargs={'company_code': company_code, 'pk': account.pk}
        )
    else:
        base_download_url = f"/chart_of_accounts/detail/{account.pk}/pdf/"
    download_url = f"{base_download_url}?{urlencode(query_data)}" if query_data else base_download_url

    fiscal_years = _get_all_fiscal_years(request)
    fy_id = selected_fy.id if selected_fy else None

    context = {
        'account': account,
        'journal': journal_page,
        'date_from': date_from,
        'date_to': date_to,
        'download_url': download_url,
        'fiscal_years': fiscal_years,
        'selected_fy': selected_fy,
        'fy_id': fy_id,
    }
    return render(request, 'chart_of_accounts/account_detail.html', context)


@login_required
def account_ledger_download_pdf(request, company_code, pk):
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from datetime import datetime

    account = get_object_or_404(ChartOfAccounts, pk=pk)
    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (
            getattr(request.user, 'is_superuser', False)
            or can_view_chart(request.user)
            or can_view_journal(request.user)
            or has_reports_access
        ):
            messages.error(request, 'You do not have permission to download this account ledger.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download this account ledger.')
        return redirect_with_company('accounts-list')

    company_db = getattr(request, 'company_db', 'default')

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    filter_preset = request.GET.get('filter_preset', '')
    fy_id = request.GET.get('fy_id', '')
    
    if fy_id:
        try:
            from system_settings.models import FiscalYear
            fy = FiscalYear.objects.using(company_db).get(pk=int(fy_id))
            date_from = fy.start_date.strftime('%Y-%m-%d')
            date_to = fy.end_date.strftime('%Y-%m-%d')
        except Exception:
            pass
    
    if not date_from or not date_to:
        if filter_preset:
            date_from, date_to = _apply_filter_preset(filter_preset)

    rows = []
    try:
        jl_qs = JournalLine.objects.using(company_db).filter(
            account=account,
            journal__status='posted',
            status=True,
        ).select_related('journal').order_by('journal__date', 'id')

        if date_from:
            try:
                jl_qs = jl_qs.filter(
                    journal__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
                )
            except Exception:
                pass

        if date_to:
            try:
                jl_qs = jl_qs.filter(
                    journal__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
                )
            except Exception:
                pass

        all_refs = [jl.journal.reference or '' for jl in jl_qs]
        inv_numbers = set()
        bill_numbers = set()
        payment_numbers = set()
        for ref in all_refs:
            m = re.search(r'\bIN([0-9][0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
            if m:
                inv_numbers.add('IN' + m.group(1))
            m2 = re.search(r'\bBN([0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
            if m2:
                bill_numbers.add('BN' + m2.group(1))
            m3 = re.search(r'Payment\s*#(\d+)', ref, re.IGNORECASE)
            if m3:
                payment_numbers.add(int(m3.group(1)))

        from Purchase.models import BillPayment
        from sales.models import InvPayment

        invoice_map = {
            inv.inv_number: inv
            for inv in SalesInvoice.objects.using(company_db).filter(inv_number__in=inv_numbers)
            .select_related('customer')
        } if inv_numbers else {}

        bill_map = {
            bill.bill_number: bill
            for bill in Bill.objects.using(company_db).filter(bill_number__in=bill_numbers)
            .select_related('vendor')
        } if bill_numbers else {}

        bill_payment_map = {
            bp.payment_number: bp
            for bp in BillPayment.objects.using(company_db).filter(payment_number__in=payment_numbers)
            .select_related('vendor')
        } if payment_numbers else {}

        inv_payment_map = {
            ip.payment_number: ip
            for ip in InvPayment.objects.using(company_db).filter(payment_number__in=payment_numbers)
            .select_related('customer')
        } if payment_numbers else {}

        running_balance = 0.0
        for jl in jl_qs:
            debit_amt = float(jl.debit or 0)
            credit_amt = float(jl.credit or 0)
            running_balance += debit_amt - credit_amt

            ref = (jl.journal.reference or '').strip()
            narration = (jl.journal.narration or '').strip().lower()
            expense_obj = None
            expense_type = None

            if ref.startswith('Payment'):
                m_pay = re.search(r'Payment\s*#(\d+)', ref, re.IGNORECASE)
                if m_pay:
                    payment_num = int(m_pay.group(1))
                    if 'received from' in narration or 'payment received' in narration:
                        if payment_num in inv_payment_map:
                            expense_obj = inv_payment_map[payment_num]
                            expense_type = 'inv_payment'
                    elif 'payment to vendor' in narration or 'payment to' in narration:
                        if payment_num in bill_payment_map:
                            expense_obj = bill_payment_map[payment_num]
                            expense_type = 'bill_payment'
                    else:
                        if payment_num in bill_payment_map:
                            expense_obj = bill_payment_map[payment_num]
                            expense_type = 'bill_payment'
                        elif payment_num in inv_payment_map:
                            expense_obj = inv_payment_map[payment_num]
                            expense_type = 'inv_payment'

            if ref.startswith('Expense'):
                try:
                    parts = ref.split()
                    if len(parts) >= 2:
                        expense_obj = Expense.objects.using(company_db).filter(pk=int(parts[1]), status=True).first()
                        if expense_obj:
                            expense_type = 'expense'
                except Exception:
                    pass

            if not expense_obj and ref:
                inv = invoice_map.get(ref)
                if inv:
                    expense_obj = inv
                    expense_type = 'invoice'

            if not expense_obj and ref:
                bill = bill_map.get(ref)
                if bill:
                    expense_obj = bill
                    expense_type = 'bill'

            if not expense_obj:
                expense_obj = jl.journal
                expense_type = 'journal'

            party_name = ''
            try:
                if expense_type == 'invoice' and getattr(expense_obj, 'customer', None):
                    party_name = str(expense_obj.customer)
                elif expense_type == 'bill' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                elif expense_type == 'expense' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                elif expense_type == 'bill_payment' and getattr(expense_obj, 'vendor', None):
                    party_name = str(expense_obj.vendor)
                elif expense_type == 'inv_payment' and getattr(expense_obj, 'customer', None):
                    party_name = str(expense_obj.customer)
                elif expense_type == 'journal' and ref and ('reversal' in ref.lower() or 'cancel' in ref.lower()):
                    bill_match = re.search(r'\b(BN[0-9A-Za-z\-_/]+)\b', ref, re.IGNORECASE)
                    if bill_match:
                        bill_ref = bill_match.group(1)
                        if bill_ref in bill_map:
                            original_bill = bill_map[bill_ref]
                            if original_bill.vendor:
                                party_name = str(original_bill.vendor)
                    if not party_name:
                        inv_match = re.search(r'\b(IN[0-9][0-9A-Za-z\-_/]*)\b', ref, re.IGNORECASE)
                        if inv_match:
                            inv_ref = inv_match.group(1)
                            if inv_ref in invoice_map:
                                original_inv = invoice_map[inv_ref]
                                if original_inv.customer:
                                    party_name = str(original_inv.customer)
                    if not party_name:
                        pay_match = re.search(r'(?:PAY|Payment)[- ]?(\d+)', ref, re.IGNORECASE)
                        if pay_match:
                            payment_num = int(pay_match.group(1))
                            if payment_num in bill_payment_map:
                                payment = bill_payment_map[payment_num]
                                if payment.vendor:
                                    party_name = str(payment.vendor)
                            elif payment_num in inv_payment_map:
                                payment = inv_payment_map[payment_num]
                                if payment.customer:
                                    party_name = str(payment.customer)
            except Exception:
                pass

            reference_display = ref
            try:
                if expense_type == 'expense' and expense_obj:
                    reference_display = f"Expense #{expense_obj.pk}"
                elif expense_type == 'invoice' and expense_obj:
                    reference_display = f"Invoice #{getattr(expense_obj, 'inv_number', ref) or ref}"
                elif expense_type == 'bill' and expense_obj:
                    reference_display = f"Bill {getattr(expense_obj, 'bill_number', ref) or ref}"
                elif expense_type == 'bill_payment' and expense_obj:
                    reference_display = f"Payment #{expense_obj.payment_number}"
                elif expense_type == 'inv_payment' and expense_obj:
                    reference_display = f"Payment #{expense_obj.payment_number}"
                elif expense_type == 'journal':
                    reference_display = f"Journal {ref}".strip() if ref else f"Journal #{jl.journal.pk}"
            except Exception:
                pass

            rows.append({
                'date': jl.journal.date,
                'party': party_name,
                'reference': reference_display,
                'account': jl.account.name,
                'debit': debit_amt,
                'credit': credit_amt,
                'running_balance_display': (
                    f"{abs(running_balance):.2f} {'Dr' if running_balance >= 0 else 'Cr'}"
                ),
            })
    except Exception:
        logger.exception(f"account_ledger_download_pdf query failed for pk={pk}")
        rows = []

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", (account.name or "account")).strip("_")
    filename = f"ledger_{account.pk}_{safe_name}.pdf" if safe_name else f"ledger_{account.pk}.pdf"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=15,
        title=f'Account Ledger - {account.name}', author='LyraERP'
    )

    font_name, font_registered = _register_dejavu_font()

    styles = getSampleStyleSheet()
    title_style = _make_title_style(styles, font_name)
    subtitle_style = _make_subtitle_style(styles, font_name)
    amount_style = _make_amount_style(styles, font_name)
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 8
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke
    styles['Heading2'].fontSize = 10

    elements = []
    elements.append(Paragraph(f"ACCOUNT LEDGER - {account.name.upper()}", title_style))
    period_text = (
        f"From {date_from or '-'} To {date_to or '-'}"
        if date_from or date_to else "All Periods"
    )
    elements.append(Paragraph(period_text, subtitle_style))
    elements.append(Spacer(1, 6))

    table_data = [[
        Paragraph("<b>Date</b>", styles['Heading2']),
        Paragraph("<b>Party</b>", styles['Heading2']),
        Paragraph("<b>Reference</b>", styles['Heading2']),
        Paragraph("<b>Account</b>", styles['Heading2']),
        Paragraph("<b>Debit</b>", styles['Heading2']),
        Paragraph("<b>Credit</b>", styles['Heading2']),
        Paragraph("<b>Running Balance</b>", styles['Heading2']),
    ]]

    for r in rows:
        date_val = r.get('date')
        try:
            date_display = date_val.strftime('%d-%m-%Y') if date_val else ''
        except Exception:
            date_display = str(date_val or '')
        table_data.append([
            date_display,
            r.get('party', ''),
            Paragraph(r.get('reference', ''), styles['Normal']),
            r.get('account', ''),
            Paragraph(f"{float(r.get('debit') or 0):.2f}", amount_style),
            Paragraph(f"{float(r.get('credit') or 0):.2f}", amount_style),
            Paragraph(r.get('running_balance_display', ''), amount_style),
        ])

    ledger_table = Table(
        table_data, repeatRows=1,
        colWidths=[70, 100, 190, 130, 65, 65, 90]
    )
    ledger_table.setStyle(_standard_table_style(font_name))
    elements.append(ledger_table)

    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    return response


# =============================================================================
# HELPERS
# =============================================================================

def _get_all_fiscal_years(request):
    try:
        from system_settings.models import FiscalYear
        company_db = getattr(request, 'company_db', 'default')
        return list(FiscalYear.objects.using(company_db).order_by('-start_date'))
    except Exception:
        return []


def _get_selected_fy(request):
    from datetime import date as _date
    try:
        from system_settings.models import FiscalYear
        company_db = getattr(request, 'company_db', 'default')
        fy_id = request.GET.get('fy_id', '')

        if fy_id == 'all':
            return None, None, None

        if fy_id:
            try:
                fy = FiscalYear.objects.using(company_db).get(pk=int(fy_id))
                return fy, fy.start_date, fy.end_date
            except (FiscalYear.DoesNotExist, ValueError):
                pass

        today = _date.today()
        fy = FiscalYear.objects.using(company_db).filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if fy:
            return fy, fy.start_date, fy.end_date

    except Exception:
        pass

    return None, None, None


def _get_fy_start(request, as_of_date):
    try:
        from system_settings.models import FiscalYear
        company_db = getattr(request, 'company_db', 'default')
        fy = FiscalYear.objects.using(company_db).filter(
            start_date__lte=as_of_date,
            end_date__gte=as_of_date
        ).first()
        if fy:
            return fy.start_date
    except Exception:
        logger.warning(f"FY lookup failed for {as_of_date}")
    return None


# =============================================================================
# PARTY LINKING HELPERS
# =============================================================================

def _get_linked_vendor_pk(customer_pk):
    from django.apps import apps
    try:
        CustModel = apps.get_model('customer', 'Customer')
        cust = CustModel.objects.filter(pk=customer_pk).first()
        if not cust or not getattr(cust, 'is_vendor', False):
            return None, None
        cust_email = getattr(cust, 'email', None)
        cust_name = str(cust)
        for app_label, model_name in [('Purchase', 'Vendor'), ('expenses', 'Vendor'), ('Purchase', 'Supplier')]:
            try:
                VendModel = apps.get_model(app_label, model_name)
            except LookupError:
                continue
            vendor = None
            if cust_email:
                vendor = VendModel.objects.filter(email=cust_email).first()
            if not vendor:
                vendor = VendModel.objects.filter(name=cust_name).first()
            if not vendor and hasattr(cust, 'first_name'):
                try:
                    vendor = VendModel.objects.filter(
                        first_name=cust.first_name,
                        last_name=getattr(cust, 'last_name', '')
                    ).first()
                except Exception:
                    pass
            if vendor:
                return vendor.pk, str(vendor)
    except Exception:
        pass
    return None, None


def _get_linked_customer_pk(vendor_pk):
    from django.apps import apps
    try:
        vendor_obj = None
        vendor_email = None
        vendor_name = None
        for app_label, model_name in [('Purchase', 'Vendor'), ('expenses', 'Vendor'), ('Purchase', 'Supplier')]:
            try:
                VendModel = apps.get_model(app_label, model_name)
                v = VendModel.objects.filter(pk=vendor_pk).first()
                if v:
                    vendor_obj = v
                    vendor_email = getattr(v, 'email', None)
                    vendor_name = str(v)
                    break
            except LookupError:
                continue
        if not vendor_obj:
            return None, None

        CustModel = apps.get_model('customer', 'Customer')
        customer = None
        if vendor_email:
            customer = CustModel.objects.filter(email=vendor_email, is_vendor=True).first()
        if not customer and vendor_name:
            if hasattr(CustModel, 'name'):
                customer = CustModel.objects.filter(name=vendor_name, is_vendor=True).first()
            if not customer:
                parts = vendor_name.strip().split(' ', 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ''
                try:
                    customer = CustModel.objects.filter(
                        first_name=first, last_name=last, is_vendor=True
                    ).first()
                except Exception:
                    pass
        if customer:
            return customer.pk, str(customer)
    except Exception:
        pass
    return None, None


def _get_vendor_journal_ids(vendor_pk):
    import re as re_module
    bill_numbers = [
        str(b.bill_number).strip()
        for b in Bill.objects.filter(vendor_id=vendor_pk) if b.bill_number
    ]
    expense_ids = [e.id for e in Expense.objects.filter(vendor_id=vendor_pk)]
    payment_numbers = []
    try:
        from Purchase.models import BillPayment
        payment_numbers = [
            str(p.payment_number).strip()
            for p in BillPayment.objects.filter(vendor_id=vendor_pk) if p.payment_number
        ]
    except Exception:
        pass

    all_journals = JournalEntry.objects.filter(status='posted')
    valid_ids = []
    related_items = set()

    for journal in all_journals:
        ref = str(journal.reference or '')
        ref_lower = ref.lower()
        is_valid = False
        is_reversal = 'Reversal' in ref or 'Cancel' in ref
        has_vendor_payment = False

        for pay_num in payment_numbers:
            if not pay_num:
                continue
            if (
                re_module.search(rf'Payment\s+#{re_module.escape(pay_num)}(?!\d)', ref, re_module.IGNORECASE)
                or re_module.search(rf'PAY-{re_module.escape(pay_num)}(?!\d|-)', ref, re_module.IGNORECASE)
                or re_module.search(rf'Payment-{re_module.escape(pay_num)}(?!\d)', ref, re_module.IGNORECASE)
            ):
                try:
                    from Purchase.models import BillPayment as _BP
                    if (
                        _BP.objects.filter(payment_number=pay_num, vendor_id=vendor_pk).exists()
                        or _BP.objects.filter(
                            payment_number__iexact=f'PAY-{pay_num}', vendor_id=vendor_pk
                        ).exists()
                    ):
                        try:
                            from journal.models import JournalLine as _JL
                            if (
                                _JL.objects.filter(journal=journal, account__name__icontains='creditor').exists()
                                or _JL.objects.filter(journal=journal, account__name__icontains='payable').exists()
                            ):
                                has_vendor_payment = True
                                break
                        except Exception:
                            has_vendor_payment = True
                            break
                except Exception:
                    has_vendor_payment = True
                    break

        bill_in_ref = any(bn and bn.lower() in ref_lower for bn in bill_numbers)

        if is_reversal:
            if has_vendor_payment or bill_in_ref:
                is_valid = True
                for bm in re_module.findall(r'(BN\d+|BILL-\d+)', ref):
                    related_items.add(bm)
        else:
            if any(bn and bn.lower() in ref_lower for bn in bill_numbers):
                is_valid = True
            if not is_valid and any(f"Expense {eid}" in ref for eid in expense_ids):
                is_valid = True
            if not is_valid and has_vendor_payment:
                is_valid = True

        if is_valid:
            valid_ids.append(journal.id)

    for journal in all_journals:
        ref = str(journal.reference or '')
        if journal.id not in valid_ids:
            if any(ri in ref for ri in related_items):
                valid_ids.append(journal.id)

    return valid_ids


def _get_customer_journal_ids(customer_pk, party_name):
    import re as re_module
    inv_numbers = [
        str(i.inv_number).strip()
        for i in SalesInvoice.objects.filter(customer_id=customer_pk) if i.inv_number
    ]
    payment_numbers = []
    try:
        from sales.models import InvPayment
        payment_numbers = [
            str(p.payment_number).strip()
            for p in InvPayment.objects.filter(customer_id=customer_pk) if p.payment_number
        ]
    except Exception:
        pass

    all_journals = JournalEntry.objects.filter(status='posted')
    valid_ids = []
    related_bills = set()

    for journal in all_journals:
        ref = str(journal.reference or '')
        is_valid = False
        is_reversal = 'Reversal' in ref or 'Cancel' in ref
        has_customer_payment = False

        for pay_num in payment_numbers:
            if not pay_num:
                continue
            if (
                re_module.search(rf'Payment\s+#{re_module.escape(pay_num)}(?!\d)', ref, re_module.IGNORECASE)
                or re_module.search(rf'PAY-{re_module.escape(pay_num)}(?!\d|-)', ref, re_module.IGNORECASE)
                or re_module.search(rf'PR-{re_module.escape(pay_num)}(?!\d)', ref, re_module.IGNORECASE)
                or re_module.search(rf'Payment-{re_module.escape(pay_num)}(?!\d)', ref, re_module.IGNORECASE)
            ):
                try:
                    from sales.models import InvPayment as _IP
                    if _IP.objects.filter(payment_number=pay_num, customer_id=customer_pk).exists():
                        try:
                            from journal.models import JournalLine as _JL
                            if (
                                _JL.objects.filter(journal=journal, account__name__icontains='debtor').exists()
                                or _JL.objects.filter(journal=journal, account__name__icontains='receivable').exists()
                            ):
                                has_customer_payment = True
                                break
                        except Exception:
                            has_customer_payment = True
                            break
                except Exception:
                    has_customer_payment = True
                    break

        if is_reversal:
            if has_customer_payment:
                is_valid = True
            else:
                for inv_num in inv_numbers:
                    if inv_num and inv_num.lower() in ref.lower():
                        is_valid = True
                        break
            if is_valid:
                for bm in re_module.findall(r'(BN\d+|BILL-\d+)', ref):
                    related_bills.add(bm)
        else:
            for inv_num in inv_numbers:
                if not inv_num:
                    continue
                ref_low = ref.lower()
                inv_low = inv_num.lower()
                if inv_low in ref_low or f'in{inv_low}' in ref_low or f'inv-{inv_low}' in ref_low:
                    is_valid = True
                    break
            if not is_valid and has_customer_payment:
                is_valid = True
            if not is_valid and party_name:
                pname = str(party_name).lower()
                if pname in ref.lower() or pname in str(journal.narration or '').lower():
                    is_valid = True

        if is_valid:
            valid_ids.append(journal.id)

    return valid_ids


# =============================================================================
# SHARED PDF / FONT HELPERS
# =============================================================================

def _register_dejavu_font():
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        from django.conf import settings
        static_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
        font_paths = [
            static_path,
            'C:/Windows/Fonts/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Supplemental/DejaVuSans.ttf',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                pdfmetrics.registerFont(TTFont('DejaVuSans', fp))
                return 'DejaVuSans', True
    except Exception:
        pass
    return 'Helvetica', False


def _make_title_style(styles, font_name):
    return ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, textColor=colors.HexColor('#55588b'),
        spaceAfter=8, alignment=TA_CENTER, fontName=font_name,
    )


def _make_subtitle_style(styles, font_name):
    return ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#55588b'),
        spaceAfter=6, alignment=TA_CENTER, fontName=font_name,
    )


def _make_amount_style(styles, font_name):
    return ParagraphStyle(
        'AmountRight', parent=styles['Normal'],
        fontSize=8, alignment=TA_RIGHT, fontName=font_name,
    )


def _standard_table_style(font_name):
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (3, -1), 'LEFT'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])


def _make_footer(font_name):
    page_count = [0]

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 6)
        canvas.setFillColor(colors.grey)
        canvas.drawString(30, 20, "POWERED BY LyraERP")
        page_num = canvas.getPageNumber()
        page_count[0] = max(page_count[0], page_num)
        canvas.drawRightString(812, 20, f"Page {page_num} of {page_count[0]}")
        canvas.restoreState()

    return add_footer


# =============================================================================
# PARTY TRANSACTIONS
# =============================================================================

@login_required
def party_transactions(request, party_type, pk):
    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (
            getattr(request.user, 'is_superuser', False)
            or can_view_chart(request.user)
            or can_view_journal(request.user)
            or has_reports_access
        ):
            messages.error(request, 'You do not have permission to view transactions.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view transactions.')
        return redirect_with_company('accounts-list')

    from datetime import datetime
    from django.apps import apps

    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    filter_preset = request.GET.get('filter_preset', '')
    
    if selected_fy and not date_from and not date_to and not filter_preset:
        date_from = fy_from_date.strftime('%Y-%m-%d') if fy_from_date else ''
        date_to = fy_to_date.strftime('%Y-%m-%d') if fy_to_date else ''
    elif filter_preset:
        date_from, date_to = _apply_filter_preset(filter_preset)

    party_name = None
    try:
        if party_type == 'customer':
            obj = apps.get_model('customer', 'Customer').objects.filter(pk=pk).first()
            if obj:
                party_name = str(obj)
        else:
            for app_label, model_name in [('Purchase', 'Vendor'), ('expenses', 'Vendor'), ('Purchase', 'Supplier')]:
                try:
                    obj = apps.get_model(app_label, model_name).objects.filter(pk=pk).first()
                    if obj:
                        party_name = str(obj)
                        break
                except LookupError:
                    continue
    except Exception:
        pass
    if not party_name:
        party_name = f"{party_type.title()} {pk}"

    is_both = False
    linked_cust_pk = None
    linked_vend_pk = None

    if party_type == 'customer':
        linked_vend_pk, _ = _get_linked_vendor_pk(pk)
        if linked_vend_pk:
            is_both = True
    else:
        linked_cust_pk, _ = _get_linked_customer_pk(pk)
        if linked_cust_pk:
            is_both = True

    if filter_preset:
        date_from, date_to = _apply_filter_preset(filter_preset)

    valid_ids = []
    try:
        if party_type == 'customer':
            valid_ids = _get_customer_journal_ids(pk, party_name)
            if is_both and linked_vend_pk:
                valid_ids = list(set(valid_ids + _get_vendor_journal_ids(linked_vend_pk)))
        else:
            valid_ids = _get_vendor_journal_ids(pk)
            if is_both and linked_cust_pk:
                valid_ids = list(set(valid_ids + _get_customer_journal_ids(linked_cust_pk, party_name)))
    except Exception:
        logger.exception(f"party_transactions journal lookup failed for {party_type} pk={pk}")
        valid_ids = []

    journal_entries = (
        JournalEntry.objects.filter(id__in=valid_ids)
        if valid_ids else JournalEntry.objects.none()
    )

    if date_from:
        try:
            journal_entries = journal_entries.filter(
                date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
            )
        except Exception:
            pass
    if date_to:
        try:
            journal_entries = journal_entries.filter(
                date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
            )
        except Exception:
            pass

    journal = []
    running_balance = 0
    jl_qs = (
        JournalLine.objects
        .filter(journal__in=journal_entries, status=True)
        .select_related('journal', 'account')
        .order_by('journal__date', 'id')
    )

    for jl in jl_qs:
        debit_amt = float(jl.debit or 0)
        credit_amt = float(jl.credit or 0)
        running_balance += debit_amt - credit_amt
        amt = debit_amt if jl.debit else credit_amt
        journal.append({
            'date': jl.journal.date,
            'expense': jl.journal,
            'expense_type': 'journal',
            'journal_pk': jl.journal.pk,
            'account': jl.account.name,
            'amount': amt,
            'debit': debit_amt,
            'credit': credit_amt,
            'running_balance': abs(running_balance),
            'running_balance_display': (
                f"{abs(running_balance):.2f} {'Dr' if running_balance >= 0 else 'Cr'}"
            ),
            'party_name': party_name,
            'party_type': party_type,
            'party_pk': pk,
        })

    paginator = Paginator(journal, 10)
    journal_page = paginator.get_page(request.GET.get('page'))

    try:
        qs = request.GET.copy()
        qs.pop('page', None)
        querystring = qs.urlencode()
    except Exception:
        querystring = ''

    company_code = None
    try:
        company_code = request.resolver_match.kwargs.get('company_code')
    except Exception:
        pass
    if not company_code:
        try:
            parts = [p for p in (request.path or '').split('/') if p]
            company_code = parts[0] if parts else None
        except Exception:
            pass

    if company_code:
        download_url = reverse('party_transactions_pdf', kwargs={
            'company_code': company_code, 'party_type': party_type, 'pk': pk,
        })
    else:
        download_url = reverse('party_transactions_pdf', kwargs={
            'party_type': party_type, 'pk': pk,
        })
    if querystring:
        download_url = f"{download_url}?{querystring}"

    display_role = (
        "Customer & Vendor" if is_both
        else ("Customer" if party_type == 'customer' else "Vendor")
    )

    fiscal_years = _get_all_fiscal_years(request)
    fy_id = selected_fy.id if selected_fy else None

    context = {
        'journal': journal_page,
        'party_type': party_type,
        'party_pk': pk,
        'party_name': party_name,
        'display_role': display_role,
        'is_both': is_both,
        'date_from': date_from,
        'date_to': date_to,
        'filter_preset': filter_preset,
        'querystring': querystring,
        'download_url': download_url,
        'fiscal_years': fiscal_years,
        'selected_fy': selected_fy,
        'fy_id': fy_id,
    }
    return render(request, 'chart_of_accounts/party_transactions.html', context)


@login_required
def party_transactions_pdf(request, party_type, pk, company_code=''):
    from datetime import datetime, date
    from django.apps import apps
    from system_settings.models import FiscalYear

    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (
            getattr(request.user, 'is_superuser', False)
            or can_view_chart(request.user)
            or can_view_journal(request.user)
            or has_reports_access
        ):
            messages.error(request, 'You do not have permission to download this report.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download this report.')
        return redirect_with_company('accounts-list')

    fy_id = request.GET.get('fy_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    filter_preset = request.GET.get('filter_preset', '')
    
    if fy_id:
        try:
            fy = FiscalYear.objects.get(pk=int(fy_id))
            date_from = fy.start_date.strftime('%Y-%m-%d')
            date_to = fy.end_date.strftime('%Y-%m-%d')
        except Exception:
            pass
    
    if not date_from or not date_to:
        if filter_preset:
            preset_from, preset_to = _apply_filter_preset(filter_preset)
            if preset_from:
                date_from = preset_from
            if preset_to:
                date_to = preset_to

    party_name = None
    try:
        if party_type == 'customer':
            obj = apps.get_model('customer', 'Customer').objects.filter(pk=pk).first()
            if obj:
                party_name = str(obj)
        else:
            for app_label, model_name in [('Purchase', 'Vendor'), ('expenses', 'Vendor'), ('Purchase', 'Supplier')]:
                try:
                    obj = apps.get_model(app_label, model_name).objects.filter(pk=pk).first()
                    if obj:
                        party_name = str(obj)
                        break
                except LookupError:
                    continue
    except Exception:
        pass
    if not party_name:
        party_name = f"{party_type.title()} {pk}"

    is_both = False
    linked_cust_pk = None
    linked_vend_pk = None

    if party_type == 'customer':
        linked_vend_pk, _ = _get_linked_vendor_pk(pk)
        if linked_vend_pk:
            is_both = True
    else:
        linked_cust_pk, _ = _get_linked_customer_pk(pk)
        if linked_cust_pk:
            is_both = True

    if filter_preset:
        date_from, date_to = _apply_filter_preset(filter_preset)

    valid_ids = []
    try:
        if party_type == 'customer':
            valid_ids = _get_customer_journal_ids(pk, party_name)
            if is_both and linked_vend_pk:
                valid_ids = list(set(valid_ids + _get_vendor_journal_ids(linked_vend_pk)))
        else:
            valid_ids = _get_vendor_journal_ids(pk)
            if is_both and linked_cust_pk:
                valid_ids = list(set(valid_ids + _get_customer_journal_ids(linked_cust_pk, party_name)))
    except Exception:
        valid_ids = []

    journal_entries = (
        JournalEntry.objects.filter(id__in=valid_ids)
        if valid_ids else JournalEntry.objects.none()
    )

    if date_from:
        try:
            journal_entries = journal_entries.filter(
                date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
            )
        except Exception:
            pass
    if date_to:
        try:
            journal_entries = journal_entries.filter(
                date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
            )
        except Exception:
            pass

    journal = []
    running_balance = 0
    jl_qs = (
        JournalLine.objects
        .filter(journal__in=journal_entries, status=True)
        .select_related('journal', 'account')
        .order_by('journal__date', 'id')
    )

    for jl in jl_qs:
        debit_amt = float(jl.debit or 0)
        credit_amt = float(jl.credit or 0)
        running_balance += debit_amt - credit_amt
        ref_display = ''
        if jl.journal.reference:
            ref = jl.journal.reference
            try:
                if ref.startswith('Expense '):
                    exp_id = int(ref.split()[1])
                    exp = Expense.objects.filter(pk=exp_id, status=True).first()
                    ref_display = f"Expense #{exp.pk}" if exp else ref
                elif ref.startswith('INV') or ref.startswith('IN'):
                    inv = SalesInvoice.objects.filter(inv_number=ref).first()
                    ref_display = f"Invoice #{inv.inv_number}" if inv else ref
                elif ref.startswith('BN'):
                    bill = Bill.objects.filter(bill_number=ref).first()
                    ref_display = f"Bill {bill.bill_number}" if bill else ref
                else:
                    ref_display = f"Journal {ref}"
            except Exception:
                ref_display = ref
        else:
            ref_display = f"Journal #{jl.journal.pk}"

        journal.append({
            'date': jl.journal.date,
            'reference': ref_display,
            'account': jl.account.name,
            'debit': debit_amt,
            'credit': credit_amt,
            'running_balance_display': (
                f"{abs(running_balance):.2f} {'Dr' if running_balance >= 0 else 'Cr'}"
            ),
        })

    response = HttpResponse(content_type='application/pdf')
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", (party_name or "party")).strip("_")
    filename = f"party_ledger_{party_type}_{pk}_{safe_name}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=15,
        title=f'Party Ledger - {party_name}', author='LyraERP'
    )

    font_name, _ = _register_dejavu_font()
    styles = getSampleStyleSheet()
    title_style = _make_title_style(styles, font_name)
    subtitle_style = _make_subtitle_style(styles, font_name)
    amount_style = _make_amount_style(styles, font_name)
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 8
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke
    styles['Heading2'].fontSize = 10

    elements = []
    role = "Customer & Vendor" if is_both else ("Customer" if party_type == 'customer' else "Vendor")
    elements.append(Paragraph(f"PARTY LEDGER - {party_name.upper()}", title_style))
    subtitle = f"Type: {role}"
    if date_from or date_to:
        subtitle += f" | From {date_from or '-'} To {date_to or '-'}"
    else:
        subtitle += " | All Periods"
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 6))

    table_data = [[
        Paragraph("<b>Date</b>", styles['Heading2']),
        Paragraph("<b>Reference</b>", styles['Heading2']),
        Paragraph("<b>Account</b>", styles['Heading2']),
        Paragraph("<b>Debit</b>", styles['Heading2']),
        Paragraph("<b>Credit</b>", styles['Heading2']),
        Paragraph("<b>Running Balance</b>", styles['Heading2']),
    ]]
    for row in journal:
        table_data.append([
            row['date'].strftime('%d-%m-%Y') if row['date'] else '',
            Paragraph(row['reference'], styles['Normal']),
            row['account'],
            Paragraph(f"{row['debit']:.2f}", amount_style),
            Paragraph(f"{row['credit']:.2f}", amount_style),
            Paragraph(row['running_balance_display'], amount_style),
        ])

    party_table = Table(table_data, repeatRows=1, colWidths=[75, 210, 140, 65, 65, 95])
    party_table.setStyle(_standard_table_style(font_name))
    elements.append(party_table)
    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    return response


@login_required
def balance_sheet_report(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_balance_sheet(request.user)):
            messages.error(request, 'You do not have permission to view Balance Sheet.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view Balance Sheet.')
        return redirect_with_company('accounts-list')

    from datetime import datetime, date

    fiscal_years   = _get_all_fiscal_years(request)
    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)

    to_date        = request.GET.get('to_date', '')
    filter_preset  = request.GET.get('filter_preset', '')

    if filter_preset:
        _, preset_to = _apply_filter_preset(filter_preset)
        if preset_to:
            to_date = preset_to

    to_date_obj = None
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except Exception:
            pass

    if fy_to_date:
        to_date_obj = min(to_date_obj, fy_to_date) if to_date_obj else fy_to_date

    as_of_date_obj  = fy_to_date or to_date_obj or date.today()
    from_date_obj   = fy_from_date or _get_fy_start(request, as_of_date_obj)

    from .balance_sheet import generate_balance_sheet
    balance_sheet_data = generate_balance_sheet(as_of_date_obj, from_date=from_date_obj)

    from urllib.parse import urlencode
    fy_id = selected_fy.id if selected_fy else None
    download_params = {}
    if fy_id:
        download_params['fy_id'] = fy_id
    if to_date:
        download_params['to_date'] = to_date
    if filter_preset:
        download_params['filter_preset'] = filter_preset
    
    from Lyraerp.utils.redirect_utils import get_company_code, get_company_redirect_url
    company_code = get_company_code(request)
    try:
        if company_code:
            download_url = get_company_redirect_url(request, 'balance_sheet_pdf')
        else:
            download_url = reverse('balance_sheet_pdf')
    except Exception:
        download_url = f"/{company_code}/chart_of_accounts/balance-sheet/pdf/" if company_code else "/chart_of_accounts/balance-sheet/pdf/"
    
    if download_params:
        download_url = f"{download_url}?{urlencode(download_params)}"

    context = {
        'balance_sheet_data': balance_sheet_data,
        'as_of_date_obj':     as_of_date_obj,
        'from_date':          str(from_date_obj) if from_date_obj else '',
        'to_date':            to_date,
        'fiscal_years':       fiscal_years,
        'selected_fy':        selected_fy,
        'download_url':       download_url,
        'fy_id':              fy_id,
    }
    return render(request, 'chart_of_accounts/balance_sheet.html', context)


@login_required
def balance_sheet_pdf(request, company_code=''):
    from datetime import datetime, date
    from system_settings.models import FiscalYear

    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_balance_sheet(request.user)):
            messages.error(request, 'You do not have permission to download Balance Sheet.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download Balance Sheet.')
        return redirect_with_company('accounts-list')

    fy_id = request.GET.get('fy_id', '')
    to_date = request.GET.get('to_date', '')
    filter_preset = request.GET.get('filter_preset', '')
    
    to_date_obj = None
    if fy_id:
        try:
            fy = FiscalYear.objects.get(pk=int(fy_id))
            to_date_obj = fy.end_date
        except Exception:
            pass
    
    if not to_date_obj:
        if filter_preset:
            _, preset_to = _apply_filter_preset(filter_preset)
            if preset_to:
                to_date = preset_to
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            except Exception:
                pass

    as_of_date_obj = to_date_obj or date.today()
    from_date_obj = _get_fy_start(request, as_of_date_obj)

    from .balance_sheet import generate_balance_sheet
    balance_sheet_data = generate_balance_sheet(as_of_date_obj, from_date=from_date_obj)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=15,
        title='Balance Sheet', author='LyraERP'
    )

    font_name, font_registered = _register_dejavu_font()
    currency = "₹" if font_registered else "Rs."

    styles = getSampleStyleSheet()
    title_style = _make_title_style(styles, font_name)
    subtitle_style = _make_subtitle_style(styles, font_name)
    amount_style = _make_amount_style(styles, font_name)
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 8
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke
    styles['Heading2'].fontSize = 9
    styles['Heading3'].fontName = font_name
    styles['Heading3'].textColor = colors.whitesmoke
    styles['Heading3'].fontSize = 8

    elements = []
    elements.append(Paragraph("BALANCE SHEET", title_style))
    date_text = (
        f"As of {as_of_date_obj.strftime('%d %B %Y')}"
        if as_of_date_obj else "As of Today"
    )
    elements.append(Paragraph(date_text, subtitle_style))
    elements.append(Spacer(1, 6))

    def build_account_rows(accounts, indent=0):
        rows = []
        for acc in accounts:
            prefix = "    " * indent
            name = f"{prefix}{acc['name']}"
            balance = f"{currency} {acc['balance']:,.2f}"
            if acc.get('is_parent'):
                rows.append([
                    Paragraph(f"<b>{name}</b>", styles['Normal']),
                    Paragraph(f"<b>{balance}</b>", amount_style),
                ])
            else:
                rows.append([Paragraph(name, styles['Normal']), Paragraph(balance, amount_style)])
            if acc.get('children'):
                rows.extend(build_account_rows(acc['children'], indent + 1))
        return rows

    main_data = [[
        Paragraph("<b>APPLICATION OF FUNDS (ASSETS)</b>", styles['Heading2']),
        Paragraph("<b>SOURCE OF FUNDS (LIABILITIES & EQUITY)</b>", styles['Heading2']),
    ]]

    asset_rows = build_account_rows(balance_sheet_data['assets'])
    asset_rows.append(['', ''])
    asset_rows.append([
        Paragraph("<b>Total Assets</b>", styles['Normal']),
        Paragraph(f"<b>{currency} {balance_sheet_data['assets_total']:,.2f}</b>", amount_style),
    ])

    liability_rows = build_account_rows(balance_sheet_data['liabilities'])
    liability_rows.append(['', ''])
    liability_rows.append([
        Paragraph("<b>Total Liabilities</b>", styles['Normal']),
        Paragraph(f"<b>{currency} {balance_sheet_data['liabilities_total']:,.2f}</b>", amount_style),
    ])

    equity_rows = [['', '']]
    equity_rows.append([Paragraph("<b>EQUITY</b>", styles['Heading3']), ''])
    equity_rows.extend(build_account_rows(balance_sheet_data['equity']))
    equity_rows.append(['', ''])
    equity_rows.append([
        Paragraph("<b>Total Equity</b>", styles['Normal']),
        Paragraph(f"<b>{currency} {balance_sheet_data['equity_total']:,.2f}</b>", amount_style),
    ])

    right_column = liability_rows + equity_rows
    max_rows = max(len(asset_rows), len(right_column))
    asset_rows += [['', '']] * (max_rows - len(asset_rows))
    right_column += [['', '']] * (max_rows - len(right_column))

    for i in range(max_rows):
        left = asset_rows[i]
        right = right_column[i]
        main_data.append([
            Table([left], colWidths=[220, 100]),
            Table([right], colWidths=[220, 100]),
        ])

    main_data.append(['', ''])
    main_data.append([
        '',
        Table([[
            Paragraph("<b>TOTAL LIABILITIES & EQUITY</b>", styles['Heading2']),
            Paragraph(
                f"<b>{currency} {balance_sheet_data['total_liabilities_and_equity']:,.2f}</b>",
                amount_style
            ),
        ]], colWidths=[220, 100]),
    ])

    main_table = Table(main_data, colWidths=[340, 340])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 6))

    if balance_sheet_data['abs_difference'] < 0.01:
        v_text = (
            f"Balance Verified: Assets ({currency} {balance_sheet_data['assets_total']:,.2f}) "
            f"= Liabilities + Equity ({currency} {balance_sheet_data['total_liabilities_and_equity']:,.2f})"
        )
        v_color = colors.green
    else:
        v_text = (
            f"Balance Mismatch: Assets ({currency} {balance_sheet_data['assets_total']:,.2f}) "
            f"!= Liabilities + Equity. Difference: {currency} {balance_sheet_data['difference']:,.2f}"
        )
        v_color = colors.red

    elements.append(Paragraph(v_text, ParagraphStyle(
        'Verification', parent=styles['Normal'],
        fontSize=8, textColor=v_color, alignment=TA_CENTER, fontName=font_name,
    )))

    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Balance_Sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response


def debug_accounts(request):
    from .balance_sheet import get_account_balance
    all_accounts = ChartOfAccounts.objects.filter(active=True, status=True).order_by('type', 'name')
    account_info = []
    for acc in all_accounts:
        balance = get_account_balance(acc)
        account_info.append({
            'id': acc.id,
            'code': acc.code,
            'name': acc.name,
            'type': acc.type,
            'is_header': acc.is_header,
            'balance': balance,
        })
    return render(request, 'chart_of_accounts/debug_accounts.html', {'accounts': account_info})


@login_required
def profit_loss_report(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_profit_loss(request.user)):
            messages.error(request, 'You do not have permission to view Profit & Loss.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view Profit & Loss.')
        return redirect_with_company('accounts-list')

    from datetime import datetime

    fiscal_years   = _get_all_fiscal_years(request)
    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)

    from_date     = request.GET.get('from_date', '')
    to_date       = request.GET.get('to_date', '')
    filter_preset = request.GET.get('filter_preset', '')

    if filter_preset:
        preset_from, preset_to = _apply_filter_preset(filter_preset)
        if preset_from: from_date = preset_from
        if preset_to:   to_date   = preset_to

    from_date_obj = None
    to_date_obj   = None

    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        except Exception:
            pass
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except Exception:
            pass

    if fy_from_date:
        from_date_obj = max(from_date_obj, fy_from_date) if from_date_obj else fy_from_date
    if fy_to_date:
        to_date_obj = min(to_date_obj, fy_to_date) if to_date_obj else fy_to_date

    from .balance_sheet import generate_profit_loss

    as_of        = to_date_obj or datetime.now().date()
    fy_start_obj = fy_from_date or _get_fy_start(request, as_of)
    effective_to = to_date_obj  or datetime.now().date()

    pl_data = generate_profit_loss(from_date_obj, effective_to, fy_start_obj)

    # Calculate Totals for the balanced two-column grid
    # Expenses (Left): COGS + Operating Expenses
    total_expense = pl_data.get('cogs', 0) + pl_data.get('operating_expenses_total', 0)
    
    # Income (Right): Sales + Non-Operating Income
    total_income  = pl_data.get('sales', 0) + pl_data.get('non_operating_income', 0)
    
    # Final Profit/Loss adjustment to the totals for balancing the view
    net_profit = pl_data.get('net_profit_loss', 0)
    if net_profit > 0:
        total_expense += net_profit
    else:
        total_income += abs(net_profit)

    from urllib.parse import urlencode
    from Lyraerp.utils.redirect_utils import get_company_code, get_company_redirect_url
    fy_id = selected_fy.id if selected_fy else None
    download_params = {}
    if fy_id:
        download_params['fy_id'] = fy_id
    if from_date:
        download_params['from_date'] = from_date
    if to_date:
        download_params['to_date'] = to_date
    if filter_preset:
        download_params['filter_preset'] = filter_preset
    
    company_code = get_company_code(request)
    try:
        if company_code:
            download_url = get_company_redirect_url(request, 'profit_loss_pdf')
        else:
            download_url = reverse('profit_loss_pdf')
    except Exception:
        download_url = f"/{company_code}/chart_of_accounts/profit-loss/pdf/" if company_code else "/chart_of_accounts/profit-loss/pdf/"
    
    if download_params:
        download_url = f"{download_url}?{urlencode(download_params)}"

    context = {
        'pl_data':      pl_data,
        'from_date':    str(from_date_obj) if from_date_obj else '',
        'to_date':      str(to_date_obj)   if to_date_obj   else '',
        'total_expense': total_expense,
        'total_income':  total_income,
        'fiscal_years':  fiscal_years,
        'selected_fy':   selected_fy,
        'download_url':  download_url,
        'fy_id':         fy_id,
    }
    return render(request, 'chart_of_accounts/profit_loss.html', context)


@login_required
def profit_loss_pdf(request, company_code=''):
    from datetime import datetime, date
    from system_settings.models import FiscalYear

    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_profit_loss(request.user)):
            messages.error(request, 'You do not have permission to download Profit & Loss.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download Profit & Loss.')
        return redirect_with_company('accounts-list')

    fy_id = request.GET.get('fy_id', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    filter_preset = request.GET.get('filter_preset', '')

    from_date_obj = None
    to_date_obj = None
    
    if fy_id:
        try:
            fy = FiscalYear.objects.get(pk=int(fy_id))
            from_date_obj = fy.start_date
            to_date_obj = fy.end_date
        except Exception:
            pass
    
    if not to_date_obj:
        if filter_preset:
            preset_from, preset_to = _apply_filter_preset(filter_preset)
            if preset_from:
                from_date = preset_from
            if preset_to:
                to_date = preset_to
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            except Exception:
                pass
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            except Exception:
                pass

    from .balance_sheet import generate_profit_loss
    as_of = to_date_obj or date.today()
    fy_from_date_obj = _get_fy_start(request, as_of)
    effective_from = from_date_obj
    effective_to = to_date_obj or date.today()
    pl_data = generate_profit_loss(effective_from, effective_to, fy_from_date_obj)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=15,
        title='Profit & Loss Statement', author='LyraERP'
    )

    font_name, font_registered = _register_dejavu_font()
    currency = "₹" if font_registered else "Rs."

    styles = getSampleStyleSheet()
    title_style = _make_title_style(styles, font_name)
    subtitle_style = _make_subtitle_style(styles, font_name)
    amount_style = _make_amount_style(styles, font_name)
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 8
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke
    styles['Heading2'].fontSize = 9
    styles['Heading3'].fontName = font_name
    styles['Heading3'].textColor = colors.HexColor('#55588b')
    styles['Heading3'].fontSize = 8

    elements = []
    elements.append(Paragraph("PROFIT & LOSS STATEMENT", title_style))

    if from_date_obj and to_date_obj:
        date_text = f"From {from_date_obj.strftime('%d %B %Y')} to {to_date_obj.strftime('%d %B %Y')}"
    elif from_date_obj:
        date_text = f"From {from_date_obj.strftime('%d %B %Y')} onwards"
    elif to_date_obj:
        date_text = f"Up to {to_date_obj.strftime('%d %B %Y')}"
    else:
        date_text = "As of Today"
    elements.append(Paragraph(date_text, subtitle_style))
    elements.append(Spacer(1, 20))

    operating_income = []
    operating_income_total = 0
    for income_account in pl_data.get('income', []):
        if 'Direct' in income_account.get('name', ''):
            for child in income_account.get('children', []):
                operating_income.append(child)
                operating_income_total += child.get('balance', 0)

    non_operating_income = []
    non_operating_income_total = 0
    for income_account in pl_data.get('income', []):
        if 'Indirect' in income_account.get('name', ''):
            for child in income_account.get('children', []):
                non_operating_income.append(child)
                non_operating_income_total += child.get('balance', 0)

    cogs_accounts = []
    for expense in pl_data.get('expenses', []):
        if 'Direct' in expense.get('name', ''):
            for child in expense.get('children', []):
                cogs_accounts.append({'parent': child, 'children': child.get('children', [])})

    operating_expenses = []
    operating_expenses_total = 0
    for expense in pl_data.get('expenses', []):
        if 'Indirect' in expense.get('name', ''):
            operating_expenses = expense.get('children', [])
            operating_expenses_total = expense.get('balance', 0)

    # ===== TRADING ACCOUNT SUMMARY SECTION =====
    trading_data = []
    closing_stock_val = pl_data.get('closing_stock', 0)
    closing_stock_display = f"({currency} {closing_stock_val:,.2f})" if closing_stock_val > 0 else f"{currency} {closing_stock_val:,.2f}"
    
    # Add header row for trading table
    trading_data.append([
        Paragraph("<b>TRADING ACCOUNT SUMMARY</b>", styles['Heading2']),
        Paragraph("", styles['Normal']),
    ])
    
    trading_data.append([
        Paragraph("Opening Stock", styles['Normal']),
        Paragraph(f"{currency} {pl_data.get('opening_stock', 0):,.2f}", styles['Normal']),
    ])
    trading_data.append([
        Paragraph("Add: Purchases", styles['Normal']),
        Paragraph(f"{currency} {pl_data.get('purchases', 0):,.2f}", styles['Normal']),
    ])
    trading_data.append([
        Paragraph("Add: Stock Adjustments", styles['Normal']),
        Paragraph(f"{currency} {pl_data.get('stock_adjustments', 0):,.2f}", styles['Normal']),
    ])
    trading_data.append([
        Paragraph("Less: Closing Stock", styles['Normal']),
        Paragraph(closing_stock_display, styles['Normal']),
    ])
    trading_data.append([
        Paragraph("<b>Cost of Goods Sold</b>", styles['Heading3']),
        Paragraph(f"<b>{currency} {pl_data.get('cogs', 0):,.2f}</b>", styles['Heading3']),
    ])
    
    trading_table = Table(trading_data, colWidths=[450, 220])
    trading_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(trading_table)
    elements.append(Spacer(1, 10))

    # ===== MAIN P&L TABLE =====
    table_data = [[
        Paragraph("<b>EXPENSE</b>", styles['Heading2']),
        Paragraph("<b>INCOME</b>", styles['Heading2']),
    ]]
    table_data.append([
        Paragraph("<b>COST OF GOODS SOLD</b>", styles['Heading3']),
        Paragraph("<b>OPERATING INCOME</b>", styles['Heading3']),
    ])

    # Build lists for left and right sides to align properly
    left_items = []  # COGS items for left column
    right_items = []  # Income items for right column
    
    # Add Sales first
    right_items.append(Paragraph(f"Sales: {currency} {pl_data.get('sales', 0):,.2f}", styles['Normal']))
    
    # Add other operating income items (Service, etc.)
    for ni in operating_income:
        if 'Sales' not in ni.get('name', ''):
            right_items.append(Paragraph(f"{ni['name']}: {currency} {ni['balance']:,.2f}", styles['Normal']))
    
    # Add TOTAL OPERATING INCOME
    right_items.append(Paragraph(f"<b>TOTAL OPERATING INCOME: {currency} {operating_income_total:,.2f}</b>", styles['Heading3']))
    
    # Add COGS account details for left side
    for item in cogs_accounts:
        left_items.append(Paragraph(f"  {item['parent']['name']}: {currency} {item['parent']['balance']:,.2f}", styles['Normal']))
        for child in item['children']:
            left_items.append(Paragraph(f"    {child['name']}: {currency} {child['balance']:,.2f}", styles['Normal']))
    
    # Add TOTAL COGS
    left_items.append(Paragraph(f"<b>TOTAL COGS: {currency} {pl_data.get('cogs', 0):,.2f}</b>", styles['Heading3']))
    
    # Add all rows, matching left and right items
    max_rows = max(len(left_items), len(right_items))
    for i in range(max_rows):
        left_text = left_items[i] if i < len(left_items) else Paragraph("", styles['Normal'])
        right_text = right_items[i] if i < len(right_items) else Paragraph("", styles['Normal'])
        table_data.append([left_text, right_text])
    
    table_data.append([
        Paragraph("<b>OPERATING EXPENSE</b>", styles['Heading3']),
        Paragraph("<b>NON OPERATING INCOME</b>", styles['Heading3']),
    ])
    
    # Add operating expenses and non-operating income items side by side
    max_items = max(len(operating_expenses), len(non_operating_income))
    for i in range(max_items):
        exp_text = ""
        inc_text = ""
        
        if i < len(operating_expenses):
            exp = operating_expenses[i]
            exp_text = f"  {exp['name']}: {currency} {exp['balance']:,.2f}"
        if i < len(non_operating_income):
            ni = non_operating_income[i]
            inc_text = f"  {ni['name']}: {currency} {ni['balance']:,.2f}"
            
        table_data.append([
            Paragraph(exp_text, styles['Normal']),
            Paragraph(inc_text, styles['Normal']),
        ])
    
    table_data.append([
        Paragraph(f"<b>TOTAL OPEX: {currency} {operating_expenses_total:,.2f}</b>", styles['Heading3']),
        Paragraph(f"<b>TOTAL NON-OP INCOME: {currency} {non_operating_income_total:,.2f}</b>", styles['Heading3']),
    ])
    table_data.append([
        Paragraph(f"<b>NET PROFIT/LOSS: {currency} {pl_data.get('net_profit_loss', 0):,.2f}</b>", styles['Heading3']),
        Paragraph("", styles['Normal']),
    ])

    pl_table = Table(table_data, colWidths=[340, 340])
    pl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(pl_table)
    elements.append(Spacer(1, 6))

    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Profit_Loss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response


@login_required
def trial_balance_report(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_trial_balance(request.user)):
            messages.error(request, 'You do not have permission to view Trial Balance.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view Trial Balance.')
        return redirect_with_company('accounts-list')

    from datetime import datetime, date

    fiscal_years   = _get_all_fiscal_years(request)
    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)

    filter_preset = request.GET.get('filter_preset', '')
    from_date     = request.GET.get('from_date', '')
    to_date       = request.GET.get('to_date', '')

    if filter_preset:
        preset_from, preset_to = _apply_filter_preset(filter_preset)
        if preset_from: from_date = preset_from
        if preset_to:   to_date   = preset_to

    to_date_obj = None
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except Exception:
            pass

    if fy_to_date:
        to_date_obj = min(to_date_obj, fy_to_date) if to_date_obj else fy_to_date

    as_of_date_obj   = fy_to_date or to_date_obj or date.today()
    fy_from_date_obj = fy_from_date or _get_fy_start(request, as_of_date_obj)

    from .balance_sheet import generate_trial_balance
    tb_data = generate_trial_balance(as_of_date_obj, from_date=fy_from_date_obj)

    from urllib.parse import urlencode
    from Lyraerp.utils.redirect_utils import get_company_code, get_company_redirect_url
    fy_id = selected_fy.id if selected_fy else None
    download_params = {}
    if fy_id:
        download_params['fy_id'] = fy_id
    if from_date:
        download_params['from_date'] = from_date
    if to_date:
        download_params['to_date'] = to_date
    if filter_preset:
        download_params['filter_preset'] = filter_preset
    
    company_code = get_company_code(request)
    try:
        if company_code:
            download_url = get_company_redirect_url(request, 'trial_balance_pdf')
        else:
            download_url = reverse('trial_balance_pdf')
    except Exception:
        download_url = f"/{company_code}/chart_of_accounts/trial-balance/pdf/" if company_code else "/chart_of_accounts/trial-balance/pdf/"
    
    if download_params:
        download_url = f"{download_url}?{urlencode(download_params)}"

    context = {
        'tb_data':      tb_data,
        'from_date':    str(fy_from_date_obj) if fy_from_date_obj else from_date,
        'to_date':      str(to_date_obj)       if to_date_obj       else to_date,
        'fiscal_years': fiscal_years,
        'selected_fy':  selected_fy,
        'download_url': download_url,
        'fy_id':        fy_id,
    }
    return render(request, 'chart_of_accounts/trial_balance.html', context)


def trial_balance_pdf(request, company_code=''):
    from datetime import datetime, date
    from system_settings.models import FiscalYear

    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_trial_balance(request.user)):
            messages.error(request, 'You do not have permission to download Trial Balance.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download Trial Balance.')
        return redirect_with_company('accounts-list')

    fy_id = request.GET.get('fy_id', '')
    filter_preset = request.GET.get('filter_preset', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    to_date_obj = None
    
    if fy_id:
        try:
            fy = FiscalYear.objects.get(pk=int(fy_id))
            to_date_obj = fy.end_date
        except Exception:
            pass
    
    if not to_date_obj:
        if filter_preset:
            _, preset_to = _apply_filter_preset(filter_preset)
            if preset_to:
                to_date = preset_to
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            except Exception:
                pass

    as_of_date_obj = to_date_obj or date.today()
    fy_from_date_obj = _get_fy_start(request, as_of_date_obj)

    from .balance_sheet import generate_trial_balance
    tb_data = generate_trial_balance(as_of_date_obj, from_date=fy_from_date_obj)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=15,
        title='Trial Balance', author='LyraERP'
    )

    font_name, font_registered = _register_dejavu_font()
    currency = "₹" if font_registered else "Rs."

    styles = getSampleStyleSheet()
    title_style = _make_title_style(styles, font_name)
    subtitle_style = _make_subtitle_style(styles, font_name)
    amount_style = _make_amount_style(styles, font_name)
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 8
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke
    styles['Heading2'].fontSize = 10

    elements = []
    elements.append(Paragraph("TRIAL BALANCE", title_style))
    date_text = (
        f"As of {as_of_date_obj.strftime('%d %B %Y')}"
        if as_of_date_obj else "As of Today"
    )
    elements.append(Paragraph(date_text, subtitle_style))
    elements.append(Spacer(1, 6))

    table_data = [[
        Paragraph("<b>ACCOUNT NAME</b>", styles['Heading2']),
        Paragraph("<b>DEBIT (₹)</b>", styles['Heading2']),
        Paragraph("<b>CREDIT (₹)</b>", styles['Heading2']),
    ]]

    for acc in tb_data.get('accounts', []):
        debit = f"{currency} {acc.get('debit', 0):,.2f}"
        credit = f"{currency} {acc.get('credit', 0):,.2f}"
        table_data.append([
            Paragraph(acc['name'], styles['Normal']),
            Paragraph(debit, amount_style),
            Paragraph(credit, amount_style),
        ])

    table_data.append(['', '', ''])
    table_data.append([
        Paragraph("<b>TOTAL</b>", styles['Heading2']),
        Paragraph(f"<b>{currency} {tb_data.get('total_debit', 0):,.2f}</b>", amount_style),
        Paragraph(f"<b>{currency} {tb_data.get('total_credit', 0):,.2f}</b>", amount_style),
    ])

    tb_table = Table(table_data, colWidths=[350, 160, 160])
    tb_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(tb_table)
    elements.append(Spacer(1, 6))

    td = tb_data.get('total_debit', 0)
    tc = tb_data.get('total_credit', 0)
    if abs(td - tc) < 0.01:
        v_text = f"Trial Balance Verified: Debit ({currency} {td:,.2f}) = Credit ({currency} {tc:,.2f})"
        v_color = colors.green
    else:
        v_text = (
            f"Trial Balance Mismatch: Debit ({currency} {td:,.2f}) != "
            f"Credit ({currency} {tc:,.2f}). Difference: {currency} {abs(td - tc):,.2f}"
        )
        v_color = colors.red

    elements.append(Paragraph(v_text, ParagraphStyle(
        'Verification', parent=styles['Normal'],
        fontSize=8, textColor=v_color, alignment=TA_CENTER, fontName=font_name,
    )))

    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Trial_Balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response


# =============================================================================
# INVENTORY VALUATION SUMMARY
# =============================================================================
# THE FIX: Removed item__created_at filter for closed FYs.
#
# OLD broken code:
#   if selected_fy and selected_fy.status == 'closed':
#       opening_stock_items = stock_items.filter(
#           item__created_at__lte=from_datetime_start  ← BUG
#       )
#
# WHY IT BROKE: Items are created in the system when the user enters them
# (e.g. May 7, 2026), but their journal transactions are backdated to the
# actual business date (e.g. Apr 1, 2025). The filter excluded any item
# whose record was created AFTER the FY start date → "No inventory items found"
#
# FIX: Remove the created_at filter entirely. ALL active stock items are
# included. calculate_inventory_value_matching_pl() handles the date scoping
# correctly — items with no transactions in a period will return (0, 0)
# and be naturally excluded by the existing zero-value check.
# =============================================================================

@login_required
def inventory_valuation_summary(request):
    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (getattr(request.user, 'is_superuser', False) or has_reports_access):
            messages.error(request, 'You do not have permission to view Inventory Valuation Summary.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view Inventory Valuation Summary.')
        return redirect_with_company('accounts-list')

    from chart_of_accounts.inventory_match_pl import calculate_inventory_value_matching_pl, item_had_activity_by
    from datetime import datetime, timedelta
    from urllib.parse import urlencode
    from system_settings.models import FiscalYear

    try:
        company_db = getattr(request, 'company_db', 'default')
        fiscal_years = list(FiscalYear.objects.using(company_db).order_by('-start_date'))
    except Exception as e:
        logger.exception(f"inventory_valuation_summary fiscal_years lookup failed: {e}")
        fiscal_years = []

    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    filter_preset = request.GET.get('filter_preset', '')
    view_type = request.GET.get('view_type', 'closing')

    if selected_fy and not from_date and not to_date and not filter_preset:
        from_date = fy_from_date.strftime('%Y-%m-%d') if fy_from_date else ''
        to_date = fy_to_date.strftime('%Y-%m-%d') if fy_to_date else ''
    elif filter_preset:
        _, preset_to = _apply_filter_preset(filter_preset)
        if preset_to:
            to_date = preset_to
        from_date = ''

    from_date_obj = None
    to_date_obj = None
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        except Exception:
            pass
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except Exception:
            pass

    # FIX: No created_at filter — include ALL active stock items regardless of
    # when the item record was created in the system.
    stock_items = Stock.objects.select_related('item').filter(
        item__status=True
    ).order_by('item__name')

    total_inventory_value = Decimal('0.00')
    inventory_data = []

    if view_type == 'opening':
        # Opening stock date = day before the FY/period starts
        opening_stock_date = None
        if from_date_obj:
            opening_stock_date = from_date_obj - timedelta(days=1)
        elif fy_from_date:
            opening_stock_date = fy_from_date - timedelta(days=1)

        # Get base items from stock master
        items_to_check = set(stock.item for stock in stock_items)
        
        # For opening stock, check if we should include items from prior FY transactions
        # This ensures items that existed before the FY start are included
        if selected_fy and opening_stock_date:
            from Purchase.models import BillItem
            from sales.models import SalesInvoiceItem
            from Items.models import Item
            
            # Items with purchase activity before FY start
            prior_bill_item_ids = BillItem.objects.filter(
                bill__date__lte=opening_stock_date,
                product__status=True
            ).values_list('product_id', flat=True).distinct()
            
            # Fetch actual Item objects by ID
            prior_bill_items = Item.objects.filter(id__in=prior_bill_item_ids, status=True)
            items_to_check.update(prior_bill_items)
            
            # Items with sales activity before FY start
            prior_sales_item_ids = SalesInvoiceItem.objects.filter(
                sales_inv__date__lte=opening_stock_date,
                product__status=True
            ).values_list('product_id', flat=True).distinct()
            
            # Fetch actual Item objects by ID
            prior_sales_items = Item.objects.filter(id__in=prior_sales_item_ids, status=True)
            items_to_check.update(prior_sales_items)

        for item in items_to_check:
            # We calculate opening for the SAME period as the P&L, 
            # using return_opening=True to get the starting balance (which includes mid-period journals)
            qty, opening_value = calculate_inventory_value_matching_pl(
                item, 
                from_date=from_date_obj, 
                to_date=to_date_obj,
                return_opening=True
            )

            if qty > 0 or opening_value > 0:
                inventory_data.append({
                    'item': item,
                    'quantity': qty,
                    'inventory_value': opening_value,
                })
                total_inventory_value += opening_value

        comment = 'Opening Stock value at beginning of period, valued at actual purchase costs.'
        page_title = 'Opening Stock Valuation'

    else:
        # Closing stock
        # FIX: Include ALL items with stock transactions or stock on hand,
        # not just items in Stock master. Items without opening stock entries
        # but with purchase bills must still appear in inventory valuation.
        
        # Get all items from stock master
        items_to_check = set(stock.item for stock in stock_items)
        
        # For active FY, also include items from purchase bills in the period
        if selected_fy and selected_fy.status != 'closed':
            from Purchase.models import BillItem
            bill_item_ids = BillItem.objects.filter(
                bill__date__gte=from_date_obj,
                bill__date__lte=to_date_obj,
                product__status=True
            ).values_list('product_id', flat=True).distinct()
            
            # Fetch actual Item objects by ID
            from Items.models import Item
            bill_items = Item.objects.filter(id__in=bill_item_ids, status=True)
            items_to_check.update(bill_items)
        
        # For active FY, also include items from sales invoices in the period
        if selected_fy and selected_fy.status != 'closed':
            from sales.models import SalesInvoiceItem
            sales_item_ids = SalesInvoiceItem.objects.filter(
                sales_inv__date__gte=from_date_obj,
                sales_inv__date__lte=to_date_obj,
                product__status=True
            ).values_list('product_id', flat=True).distinct()
            
            # Fetch actual Item objects by ID
            from Items.models import Item
            sales_items = Item.objects.filter(id__in=sales_item_ids, status=True)
            items_to_check.update(sales_items)
        
        for item in items_to_check:
            # For CLOSED fiscal years, filter items by historical existence.
            # An item should only appear in a CLOSED FY closing stock if it had
            # activity on or before that FY's end date.
            # Example: bingo created May 8 2026 should NOT appear in FY 2025-26 
            # (which ended Mar 31 2026).
            if selected_fy and selected_fy.status == 'closed' and to_date_obj:
                if not item_had_activity_by(item, to_date_obj):
                    # Item had no activity before FY end date, skip it
                    continue

            qty, closing_value = calculate_inventory_value_matching_pl(
                item,
                from_date=from_date_obj,
                to_date=to_date_obj
            )

            # Include item if it has any positive closing quantity
            # This covers items introduced mid-year through purchases
            if qty > 0:
                inventory_data.append({
                    'item': item,
                    'quantity': qty,
                    'inventory_value': closing_value,
                })
                total_inventory_value += closing_value

        comment = 'Closing Stock calculated using P&L formula: Opening + Purchases - COGS.'
        page_title = 'Closing Stock Valuation'

    context = {
        'inventory_items': inventory_data,
        'total_inventory_value': total_inventory_value,
        'from_date': from_date,
        'to_date': to_date,
        'view_type': view_type,
        'page_title': page_title,
        'comment': comment,
        'fiscal_years': fiscal_years,
        'selected_fy': selected_fy,
        'fy_id': selected_fy.id if selected_fy else None,
    }
    return render(request, 'chart_of_accounts/inventory_valuation_summary.html', context)


@login_required
def cash_flow_report(request):
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_cash_flow(request.user)):
            messages.error(request, 'You do not have permission to view Cash Flow Statement.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to view Cash Flow Statement.')
        return redirect_with_company('accounts-list')

    from datetime import datetime

    fiscal_years   = _get_all_fiscal_years(request)
    selected_fy, fy_from_date, fy_to_date = _get_selected_fy(request)

    filter_preset = request.GET.get('filter_preset', '')
    from_date     = request.GET.get('from_date', '')
    to_date       = request.GET.get('to_date', '')

    if filter_preset:
        preset_from, preset_to = _apply_filter_preset(filter_preset)
        if preset_from: from_date = preset_from
        if preset_to:   to_date   = preset_to

    from_date_obj = None
    to_date_obj   = None

    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        except Exception:
            pass
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        except Exception:
            pass

    if fy_from_date:
        from_date_obj = max(from_date_obj, fy_from_date) if from_date_obj else fy_from_date
    if fy_to_date:
        to_date_obj = min(to_date_obj, fy_to_date) if to_date_obj else fy_to_date

    if not from_date_obj or not to_date_obj:
        today         = datetime.now().date()
        from_date_obj = today.replace(day=1)
        to_date_obj   = today

    from_date = str(from_date_obj)
    to_date   = str(to_date_obj)

    from .balance_sheet import generate_cash_flow_statement
    fy_start_date = fy_from_date or _get_fy_start(request, to_date_obj)

    try:
        cf_data = generate_cash_flow_statement(
            from_date_obj, to_date_obj, fy_start_date=fy_start_date
        )
    except ValueError as e:
        logger.error(f"cash_flow_report: {e}")
        cf_data = {
            'error': str(e),
            'operating_activities': {},
            'investing_activities': {},
            'financing_activities': {},
            'cash_movement': {},
        }
    except Exception as e:
        logger.exception(f"cash_flow_report unexpected error: {e}")
        cf_data = {
            'error': str(e),
            'operating_activities': {},
            'investing_activities': {},
            'financing_activities': {},
            'cash_movement': {},
        }

    from urllib.parse import urlencode
    from Lyraerp.utils.redirect_utils import get_company_code, get_company_redirect_url
    fy_id = selected_fy.id if selected_fy else None
    download_params = {}
    if fy_id:
        download_params['fy_id'] = fy_id
    if from_date:
        download_params['from_date'] = from_date
    if to_date:
        download_params['to_date'] = to_date
    if filter_preset:
        download_params['filter_preset'] = filter_preset
    
    company_code = get_company_code(request)
    try:
        if company_code:
            download_url = get_company_redirect_url(request, 'cash_flow_pdf')
        else:
            download_url = reverse('cash_flow_pdf')
    except Exception:
        download_url = f"/{company_code}/chart_of_accounts/cash-flow/pdf/" if company_code else "/chart_of_accounts/cash-flow/pdf/"
    
    if download_params:
        download_url = f"{download_url}?{urlencode(download_params)}"

    context = {
        'cf_data':      cf_data,
        'from_date':    from_date,
        'to_date':      to_date,
        'fiscal_years': fiscal_years,
        'selected_fy':  selected_fy,
        'download_url': download_url,
        'fy_id':        fy_id,
    }
    return render(request, 'chart_of_accounts/cash_flow_statement.html', context)


def cash_flow_pdf(request, company_code=''):
    from datetime import datetime, date
    from system_settings.models import FiscalYear

    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_cash_flow(request.user)):
            messages.error(request, 'You do not have permission to download Cash Flow Statement.')
            return redirect_with_company('accounts-list')
    except Exception:
        messages.error(request, 'You do not have permission to download Cash Flow Statement.')
        return redirect_with_company('accounts-list')

    fy_id = request.GET.get('fy_id', '')
    filter_preset = request.GET.get('filter_preset', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    from_date_obj = None
    to_date_obj = None
    
    if fy_id:
        try:
            fy = FiscalYear.objects.get(pk=int(fy_id))
            from_date_obj = fy.start_date
            to_date_obj = fy.end_date
        except Exception:
            pass
    
    if not to_date_obj:
        if filter_preset:
            preset_from, preset_to = _apply_filter_preset(filter_preset)
            if preset_from:
                from_date = preset_from
            if preset_to:
                to_date = preset_to
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            except Exception:
                pass
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            except Exception:
                pass

    if not from_date_obj or not to_date_obj:
        today = date.today()
        from_date_obj = from_date_obj or today.replace(day=1)
        to_date_obj = to_date_obj or today

    from .balance_sheet import generate_cash_flow_statement
    fy_start_date = _get_fy_start(request, to_date_obj)

    try:
        cf_data = generate_cash_flow_statement(from_date_obj, to_date_obj, fy_start_date=fy_start_date)
    except Exception as e:
        logger.exception(f"cash_flow_pdf generation error: {e}")
        cf_data = {
            'operating_activities': {}, 'investing_activities': {},
            'financing_activities': {}, 'cash_movement': {},
        }

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=15,
        title='Cash Flow Statement', author='LyraERP'
    )

    font_name, font_registered = _register_dejavu_font()
    currency = "₹" if font_registered else "Rs."

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=24, textColor=colors.HexColor('#55588b'),
        spaceAfter=30, alignment=TA_CENTER, fontName=font_name,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontSize=12, textColor=colors.HexColor('#55588b'),
        spaceAfter=20, alignment=TA_CENTER, fontName=font_name,
    )
    amount_style = _make_amount_style(styles, font_name)
    section_header_style = ParagraphStyle(
        'SectionHeader', parent=styles['Normal'],
        fontSize=11, fontName=font_name, textColor=colors.HexColor('#1e293b'),
        spaceAfter=6, spaceBefore=10,
    )
    styles['Normal'].fontName = font_name
    styles['Heading2'].fontName = font_name
    styles['Heading2'].textColor = colors.whitesmoke

    def fmt(value):
        return f"{currency} {value:,.2f}" if value else f"{currency} 0.00"

    elements = []
    elements.append(Paragraph("CASH FLOW STATEMENT", title_style))
    elements.append(Paragraph(
        f"For the period {from_date_obj.strftime('%d %B %Y')} to {to_date_obj.strftime('%d %B %Y')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 6))

    table_data = [[
        Paragraph("<b>CASH FLOW ACTIVITIES</b>", styles['Heading2']),
        Paragraph("<b>AMOUNT</b>", styles['Heading2']),
    ]]

    operating = cf_data.get('operating_activities', {})
    table_data.append([Paragraph("<b>OPERATING ACTIVITIES</b>", section_header_style), ''])
    if operating.get('net_profit_loss') is not None:
        table_data.append([
            Paragraph('Net Profit / Loss', styles['Normal']),
            Paragraph(fmt(operating['net_profit_loss']), amount_style),
        ])
    for item in operating.get('depreciation_items', []):
        table_data.append([
            Paragraph(f"  Add: {item['name']}", styles['Normal']),
            Paragraph(fmt(item['amount']), amount_style),
        ])
    for item in operating.get('working_capital_items', []):
        table_data.append([
            Paragraph(f"  {item['name']}", styles['Normal']),
            Paragraph(fmt(item['cash_impact']), amount_style),
        ])
    table_data.append([
        Paragraph('<b>Net Cash from Operating Activities</b>', styles['Normal']),
        Paragraph(f"<b>{fmt(operating.get('net_cash_from_operating', 0))}</b>", amount_style),
    ])
    table_data.append(['', ''])

    investing = cf_data.get('investing_activities', {})
    table_data.append([Paragraph("<b>INVESTING ACTIVITIES</b>", section_header_style), ''])
    if investing.get('items'):
        for item in investing['items']:
            table_data.append([
                Paragraph(f"  {item['name']}", styles['Normal']),
                Paragraph(fmt(item['adjustment']), amount_style),
            ])
    else:
        table_data.append([Paragraph("No investing activities", styles['Normal']), Paragraph(fmt(0), amount_style)])
    table_data.append([
        Paragraph('<b>Net Cash from Investing Activities</b>', styles['Normal']),
        Paragraph(f"<b>{fmt(investing.get('net_cash_from_investing', 0))}</b>", amount_style),
    ])
    table_data.append(['', ''])

    financing = cf_data.get('financing_activities', {})
    table_data.append([Paragraph("<b>FINANCING ACTIVITIES</b>", section_header_style), ''])
    if financing.get('items'):
        for item in financing['items']:
            table_data.append([
                Paragraph(f"  {item['name']}", styles['Normal']),
                Paragraph(fmt(item['adjustment']), amount_style),
            ])
    else:
        table_data.append([Paragraph("No financing activities", styles['Normal']), Paragraph(fmt(0), amount_style)])
    table_data.append([
        Paragraph('<b>Net Cash from Financing Activities</b>', styles['Normal']),
        Paragraph(f"<b>{fmt(financing.get('net_cash_from_financing', 0))}</b>", amount_style),
    ])
    table_data.append(['', ''])

    movement = cf_data.get('cash_movement', {})
    table_data.append([Paragraph("<b>CASH MOVEMENT SUMMARY</b>", section_header_style), ''])
    table_data.append([
        Paragraph('Opening Cash Balance', styles['Normal']),
        Paragraph(fmt(movement.get('opening_cash_balance', 0)), amount_style),
    ])
    table_data.append([
        Paragraph('Net Change in Cash', styles['Normal']),
        Paragraph(fmt(movement.get('net_change_in_cash', 0)), amount_style),
    ])
    table_data.append([
        Paragraph('<b>Closing Cash Balance</b>', styles['Normal']),
        Paragraph(f"<b>{fmt(movement.get('closing_cash_balance', 0))}</b>", amount_style),
    ])
    if movement.get('variance') and abs(movement['variance']) > 0.01:
        table_data.append(['', ''])
        table_data.append([
            Paragraph('Reconciliation Variance', styles['Normal']),
            Paragraph(fmt(movement['variance']), amount_style),
        ])

    cf_table = Table(table_data, colWidths=[430, 170])
    cf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#55588b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(cf_table)
    elements.append(Spacer(1, 6))

    if movement.get('is_balanced'):
        v_text = (
            f"Cash Flow Reconciled — Opening ({currency} {movement.get('opening_cash_balance', 0):,.2f}) "
            f"+ Net Change ({currency} {movement.get('net_change_in_cash', 0):,.2f}) "
            f"= Closing ({currency} {movement.get('closing_cash_balance', 0):,.2f})"
        )
        v_color = colors.green
    else:
        v_text = f"Reconciliation Variance: {currency} {movement.get('variance', 0):,.2f}"
        v_color = colors.red

    elements.append(Paragraph(v_text, ParagraphStyle(
        'Verification', parent=styles['Normal'],
        fontSize=8, textColor=v_color, alignment=TA_CENTER, fontName=font_name,
    )))

    doc.build(elements, onFirstPage=_make_footer(font_name), onLaterPages=_make_footer(font_name))
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    filename = f"Cash_Flow_Statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response
