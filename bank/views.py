from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.db import IntegrityError, transaction
from decimal import Decimal
from datetime import date
from pathlib import Path
import json
import re

from .models import Bank, BankReconciliation, BankReconciliationLine, BankStatementLine, BankRule
from .forms import ReconciliationStartForm, BankStatementUploadForm, BankRuleForm
from .reconciliation_utils import (
    create_statement_entries_from_csv,
    create_posted_journal_for_statement_line,
    fetch_statement_lines,
    parse_bank_statement_file,
    TransactionLoader,
    ReconciliationAutoMatcher,
    update_reconciliation_totals,
)
from Lyraerp.utils.thread_locals import get_current_db
from company.models import Company
from company_settings.models import CompanyBankAccount
from currencies.models import Currency
from currencies.utils import get_currency_symbol
from journal.models import JournalEntry, JournalLine
from .permissions import (
    can_view_banking,
    can_view_reconciliation,
    can_create_reconciliation,
    can_edit_reconciliation,
    can_delete_reconciliation,
)

print("[DEBUG] bank/views.py MODULE LOADED BY DJANGO")


def _get_company_db_alias(request):
    company_db = getattr(request, 'company_db', None)
    if company_db and company_db != 'default':
        return company_db
    current = get_current_db()
    return current or 'default'


def _load_reconciliation(request, reconciliation_id):
    db_alias = _get_company_db_alias(request)
    qs = BankReconciliation.objects.using(db_alias)
    reconciliation = get_object_or_404(qs, id=reconciliation_id)
    return reconciliation, db_alias


def _get_bank_currency_context(request, db_alias=None):
    db_alias = db_alias or _get_company_db_alias(request)
    company_id = getattr(request, 'company_id', None) or request.session.get('company_id')
    code = ''

    try:
        if company_id and db_alias and db_alias != 'default':
            base = Currency.objects.using(db_alias).filter(
                company_id=company_id,
                is_base=True,
                is_active=True,
            ).order_by('id').first()
            if base:
                code = (base.code or '').strip().upper()
                symbol = (base.symbol or get_currency_symbol(code) or code).strip()
                return {
                    'base_currency_code': code,
                    'base_currency_symbol': symbol,
                }
    except Exception:
        pass

    try:
        if company_id:
            company = Company.objects.using('default').filter(pk=company_id).first()
        else:
            company = Company.objects.using('default').order_by('id').first()
        code = (getattr(company, 'base_currency', None) or '').strip().upper() if company else ''
    except Exception:
        code = ''

    symbol = (get_currency_symbol(code) if code else '') or code
    return {
        'base_currency_code': code,
        'base_currency_symbol': symbol,
    }


def _reconciliation_source_from_reference(line):
    """Return user-facing source details for a bank reconciliation journal line."""
    reference = (getattr(line, 'reference', '') or '').strip()
    description = (getattr(line, 'description', '') or '').strip()
    haystack = f"{reference} {description}".lower()

    if re.search(r'\b(payment\s*#?|pay[-\s]?)\d+', haystack):
        if (line.debit_amount or Decimal('0.00')) > 0:
            return {
                'label': 'Payment Received',
                'class': 'source-in',
                'icon': 'bi-arrow-down-left-circle',
            }
        return {
            'label': 'Payment Made',
            'class': 'source-out',
            'icon': 'bi-arrow-up-right-circle',
        }
    if any(token in haystack for token in ('bank charge', 'bank fee', 'charges', 'fee')):
        return {
            'label': 'Bank Charges',
            'class': 'source-fee',
            'icon': 'bi-receipt',
        }
    if any(token in haystack for token in ('transfer', 'contra')):
        return {
            'label': 'Bank Transfer',
            'class': 'source-transfer',
            'icon': 'bi-arrow-left-right',
        }
    if any(token in haystack for token in ('opening', 'opening balance')):
        return {
            'label': 'Opening Balance',
            'class': 'source-opening',
            'icon': 'bi-box-arrow-in-right',
        }
    if 'manual' in haystack or reference.startswith('BANK-ADJ'):
        return {
            'label': 'Manual Entry',
            'class': 'source-manual',
            'icon': 'bi-pencil-square',
        }
    return {
        'label': 'Journal Entry',
        'class': 'source-journal',
        'icon': 'bi-journal-text',
    }


def _annotate_reconciliation_lines(lines, statement_lines):
    matched_by_recon_id = {
        stmt.matched_transaction_id: stmt
        for stmt in statement_lines
        if stmt.matched_transaction_id
    }

    for line in lines:
        source = _reconciliation_source_from_reference(line)
        matched_stmt = matched_by_recon_id.get(line.id)
        line.display_source_label = source['label']
        line.display_source_class = source['class']
        line.display_source_icon = source['icon']
        line.display_description = (
            (line.description or '').strip()
            or (line.reference or '').strip()
            or source['label']
        )
        line.matched_statement = matched_stmt
        if matched_stmt:
            line.match_badge_label = 'Auto matched' if line.auto_matched else 'Manually matched'
            line.match_badge_class = 'match-auto' if line.auto_matched else 'match-manual'
            if line.auto_matched:
                line.match_reason = 'Matched by rule, reference, date, or amount'
            else:
                line.match_reason = 'Matched manually'
        elif line.is_cleared:
            line.match_badge_label = 'Cleared'
            line.match_badge_class = 'match-cleared'
            line.match_reason = 'Marked cleared without a linked bank statement row'
        else:
            line.match_badge_label = 'Unmatched'
            line.match_badge_class = 'match-unmatched'
            line.match_reason = 'No bank statement match yet'
    return lines


# ─────────────────────────────────────────────────────────────
#  Bank Master CRUD
# ─────────────────────────────────────────────────────────────

def bank_list(request):
    items = Bank.objects.filter(status=True).order_by('bank_name')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'banks': [{'id': b.id, 'bank_name': b.bank_name} for b in items]
        })
    return render(request, 'bank/list.html', {'items': items})


def bank_create(request):
    next_target = request.GET.get('next') or request.POST.get('next')
    from HR.permissions import check_master_access, has_permission
    if not (has_permission(request.user, 'Company', 'Create') or
            check_master_access(request.user, 'Create')):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Masters Bank',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        name = request.POST.get('bank_name', '').strip()
        if not name:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Bank name is required'})
            return redirect_with_company(request, 'admin_dashboard')
        try:
            bank = Bank.objects.create(bank_name=name, status=True)
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'bank': {'id': bank.id, 'bank_name': bank.bank_name}
                })
            if next_target:
                url = get_company_redirect_url(request, 'admin_dashboard') + (
                    next_target if next_target.startswith('#') else '#' + next_target
                )
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
    return render(request, 'bank/create.html', {'next': next_target})


def bank_deactivate(request, pk):
    try:
        obj = Bank.objects.get(pk=pk)
        obj.status = False
        obj.save()
    except Bank.DoesNotExist:
        pass
    next_target = request.GET.get('next') or request.POST.get('next')
    if next_target:
        url = get_company_redirect_url(request, 'admin_dashboard') + (
            next_target if next_target.startswith('#') else '#' + next_target
        )
        return redirect(url)
    return redirect_with_company(request, 'admin_dashboard')


def bank_edit(request, pk):
    next_target = request.GET.get('next') or request.POST.get('next')
    try:
        obj = Bank.objects.get(pk=pk)
    except Bank.DoesNotExist:
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Masters Bank',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    if request.method == 'POST':
        name = request.POST.get('bank_name')
        status = request.POST.get('status') == 'on'
        if name:
            obj.bank_name = name
            obj.status = status
            obj.save()
            if next_target:
                url = get_company_redirect_url(request, 'admin_dashboard') + (
                    next_target if next_target.startswith('#') else '#' + next_target
                )
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')
    return render(request, 'bank/create.html', {'obj': obj, 'next': next_target})


# ─────────────────────────────────────────────────────────────
#  Banking Dashboard
# ─────────────────────────────────────────────────────────────

@login_required
def banking_dashboard(request):
    if not (getattr(request.user, 'is_superuser', False) or can_view_banking(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Banking',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    try:
        company_code = request.resolver_match.kwargs.get('company_code')
        qs = CompanyBankAccount.objects.filter(status=True).select_related('bank')
        if company_code:
            qs = qs.filter(company__code=company_code)
        accounts = qs.order_by('account_number')
    except Exception:
        accounts = CompanyBankAccount.objects.filter(
            status=True
        ).select_related('bank').order_by('account_number')

    for acc in accounts:
        acc.total_recons = acc.reconciliations.count()
        acc.reconciled_count = acc.reconciliations.filter(status='Reconciled').count()
        acc.in_progress_count = acc.reconciliations.filter(status='In Progress').count()
        last = acc.reconciliations.order_by('-end_date').first()
        acc.last_reconciled = last.reconciled_date if last and last.is_reconciled else None

    return render(request, 'bank/banking_dashboard.html', {
        'accounts': accounts,
        'page_title': 'Banking',
    })


@login_required
def reconciliation_overview(request):
    if not (getattr(request.user, 'is_superuser', False) or can_view_reconciliation(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Bank Reconciliation',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    company_code = getattr(request, 'company_code', None)
    if not company_code and request.resolver_match:
        company_code = request.resolver_match.kwargs.get('company_code')

    try:
        qs = CompanyBankAccount.objects.filter(status=True).select_related('bank')
        if company_code:
            qs = qs.filter(company__code=company_code)
        accounts = qs.order_by('account_number')
    except Exception:
        accounts = CompanyBankAccount.objects.filter(
            status=True
        ).select_related('bank').order_by('account_number')

    for acc in accounts:
        acc.total_recons = acc.reconciliations.count()
        acc.reconciled_count = acc.reconciliations.filter(status='Reconciled').count()
        acc.in_progress_count = acc.reconciliations.filter(status='In Progress').count()
        last = acc.reconciliations.order_by('-end_date').first()
        acc.last_reconciled = last.reconciled_date if last and last.is_reconciled else None

    return render(request, 'bank/reconciliation_overview.html', {
        'accounts': accounts,
        'page_title': 'Reconciliation Overview',
        'company_code': company_code,
        **_get_bank_currency_context(request),
    })


# ─────────────────────────────────────────────────────────────
#  Page 1 — Reconciliation List
# ─────────────────────────────────────────────────────────────

@login_required
def reconciliation_list(request, account_id):
    if not (getattr(request.user, 'is_superuser', False) or can_view_reconciliation(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Bank Reconciliation',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )
    reconciliations = BankReconciliation.objects.using(company_db).filter(
        bank_account=account
    ).order_by('-end_date')

    return render(request, 'bank/reconciliation_list.html', {
        'account': account,
        'reconciliations': reconciliations,
        **_get_bank_currency_context(request, company_db),
    })


# ─────────────────────────────────────────────────────────────
#  Page 2 — Start Reconciliation Form
# ─────────────────────────────────────────────────────────────

@login_required
def reconciliation_start_form(request, account_id):
    if not (getattr(request.user, 'is_superuser', False) or can_create_reconciliation(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Bank Reconciliation',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    company_code = getattr(request, 'company_code', None)
    if not company_code and request.resolver_match:
        company_code = request.resolver_match.kwargs.get('company_code')

    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )

    if request.method == 'POST':
        form = ReconciliationStartForm(request.POST, request.FILES, account=account)
        if form.is_valid():
            cd = form.cleaned_data
            start_date = cd.get('start_date')
            end_date = cd.get('end_date')
            closing_balance = cd.get('closing_balance')
            attachment = cd.get('attachment') or None

            reconciliation = None
            created = False
            processing_errors = []
            process_result = None
            loaded = 0

            try:
                with transaction.atomic(using=company_db):
                    reconciliation = BankReconciliation.objects.using(company_db).create(
                        bank_account=account,
                        end_date=end_date,
                        start_date=start_date,
                        closing_balance=closing_balance,
                        created_by=request.user,
                        attachment=attachment,
                    )
                    created = True

                    loader = TransactionLoader()
                    loaded = loader.load_journal_entries(reconciliation, using_alias=company_db)
                    update_reconciliation_totals(reconciliation)

                    if attachment:
                        process_result = _process_statement_upload(reconciliation, attachment, company_db)
                        if process_result.get('errors'):
                            raise StatementProcessingError(process_result['errors'])
            except IntegrityError:
                reconciliation = BankReconciliation.objects.using(company_db).filter(
                    bank_account=account, end_date=end_date
                ).first()
                created = False
                if not reconciliation:
                    form.add_error(None, 'Could not create reconciliation due to a database integrity error; please try again.')
            except StatementProcessingError as spe:
                processing_errors = spe.errors
                reconciliation = None
            except Exception as e:
                form.add_error(None, f'Error creating reconciliation: {e}')
                reconciliation = None

            if processing_errors:
                for err in processing_errors:
                    form.add_error('attachment', err)
            elif reconciliation:
                if created:
                    if loaded == 0:
                        messages.warning(request, (
                            f'Reconciliation #{reconciliation.id} created but no system transactions found '
                            'for this period. Upload a bank statement CSV/Excel to import transactions.'
                        ))
                    else:
                        messages.success(request, f'Reconciliation #{reconciliation.id} created and opened.')
                else:
                    messages.info(request, f'Opened existing reconciliation #{reconciliation.id} for this period.')

                if process_result:
                    messages.success(
                        request,
                        f'Imported {process_result.get("count", 0)} statement line(s) from the attachment.'
                    )
                return redirect_with_company(
                    request,
                    'reconciliation_working_screen',
                    reconciliation_id=reconciliation.id,
                )
    else:
        form = ReconciliationStartForm(account=account)

    last_recon = BankReconciliation.objects.using(company_db).filter(
        bank_account=account, status='Reconciled'
    ).order_by('-end_date').first()

    return render(request, 'bank/reconciliation_start_form.html', {
        'account':    account,
        'form':       form,
        'last_recon': last_recon,
        'company_code': company_code,
        **_get_bank_currency_context(request, company_db),
    })

class StatementProcessingError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Statement processing failed')


def _process_statement_upload(reconciliation, uploaded_file, company_db):
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ('.csv', '.xls', '.xlsx'):
        return {'errors': [f"Unsupported file type '{ext}'."]}

    uploaded_file.seek(0)
    try:
        parsed_rows, parser_errors = parse_bank_statement_file(uploaded_file)
    except ValueError as exc:
        return {'errors': [str(exc)]}

    if parser_errors:
        return {'errors': parser_errors}

    if not parsed_rows:
        return {'errors': ['No transaction rows found in the uploaded file.']}

    statement_qs = fetch_statement_lines(reconciliation, using_alias=company_db)
    statement_qs.delete()

    BankReconciliationLine.objects.using(company_db).filter(
        reconciliation=reconciliation,
    ).update(auto_matched=False, is_cleared=False)
    create_result = create_statement_entries_from_csv(
        reconciliation, parsed_rows, using_alias=company_db
    )

    # Reload system transactions so journals posted while this reconciliation existed
    # (including those from the Add Entry flow) are available before auto-matching.
    loader = TransactionLoader()
    loader.load_journal_entries(reconciliation, using_alias=company_db)

    if create_result.get('count', 0) == 0:
        return {'errors': create_result.get('errors', ['No valid statement lines created from the file.'])}

    # ── Run auto-matcher so existing journal entries get matched immediately ──
    matcher = ReconciliationAutoMatcher(reconciliation, using_alias=company_db)
    matcher.auto_match_all()
    # ─────────────────────────────────────────────────────────────────────────

    update_reconciliation_totals(reconciliation)

    return {
        'count': create_result.get('count', 0),
        'errors': [],
    }


@login_required
def bank_statement_csv_upload(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_create_reconciliation(request.user)):
        messages.error(request, 'You do not have permission to upload bank statements.')
        return redirect_with_company(request, 'reconciliation_working_screen', reconciliation_id=reconciliation_id)
    print(f"[DEBUG] bank_statement_csv_upload VIEW HIT | method={request.method} | reconciliation_id={reconciliation_id}")
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)
    print(f"[DEBUG] Reconciliation loaded | id={reconciliation.id} | db={company_db} | locked={reconciliation.is_locked()}")

    if reconciliation.is_locked():
        print(f"[DEBUG] Reconciliation {reconciliation_id} is LOCKED — redirecting to working screen")
        return redirect_with_company(
            request,
            'reconciliation_working_screen',
            reconciliation_id=reconciliation_id,
        )

    if request.method == 'POST':
        print(f"[DEBUG] POST received | FILES={list(request.FILES.keys())} | POST keys={list(request.POST.keys())}")
        form = BankStatementUploadForm(request.POST, request.FILES)
        is_valid = form.is_valid()
        print(f"[DEBUG] Form is_valid={is_valid}")
        if not is_valid:
            print(f"[DEBUG] Form errors: {form.errors}")

        if is_valid:
            statement_file = request.FILES['statement_file']
            ext = Path(statement_file.name).suffix.lower()
            print(f"[DEBUG] File received | name={statement_file.name} | ext={ext} | size={statement_file.size} bytes")
            if ext == '.pdf':
                form.add_error('statement_file', 'PDF uploads are not supported; please submit CSV or Excel files.')
                print(f"[DEBUG] Unsupported file type {ext} rejected for {statement_file.name}")
                return render(request, 'bank/bank_statement_csv_upload.html', {
                    'reconciliation': reconciliation,
                    'form': form,
                })
            result = _process_statement_upload(reconciliation, statement_file, company_db)
            if result.get('errors'):
                print(f"[DEBUG] Parser returned errors: {result['errors']}")
                return render(request, 'bank/bank_statement_csv_upload.html', {
                    'reconciliation': reconciliation,
                    'form': form,
                    'errors': result['errors'],
                })

            messages.success(
                request,
                f'Imported {result["count"]} statement line(s). Review unmatched rows below.',
            )
            print(f"[DEBUG] Upload successful — redirecting to working screen")
            return redirect_with_company(
                request,
                'reconciliation_working_screen',
                reconciliation_id=reconciliation.id,
            )
    else:
        print(f"[DEBUG] GET request — rendering empty upload form")
        form = BankStatementUploadForm()

    return render(request, 'bank/bank_statement_csv_upload.html', {
        'reconciliation': reconciliation,
        'form': form,
    })


# ─────────────────────────────────────────────────────────────
#  Page 3 — Working Screen
# ─────────────────────────────────────────────────────────────

@login_required
def reconciliation_working_screen(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_view_reconciliation(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Bank Reconciliation',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    if not reconciliation.is_locked():
        matcher = ReconciliationAutoMatcher(reconciliation, using_alias=company_db)
        matched = matcher.auto_match_all()
        if matched:
            update_reconciliation_totals(reconciliation)

    # Build the upload URL and log it so we can verify it's correct
    upload_url = get_company_redirect_url(
        request,
        'bank_statement_csv_upload',
        reconciliation_id=reconciliation.id,
    )
    print(f"[DEBUG] reconciliation_working_screen | upload_url={upload_url}")

    statement_qs = fetch_statement_lines(reconciliation, using_alias=company_db)
    statement_lines = list(statement_qs.order_by('statement_date'))
    unmatched_statements = statement_qs.filter(match_status='unmatched')
    has_unmatched = unmatched_statements.exists()

    lines_qs = BankReconciliationLine.objects.using(company_db).filter(
        reconciliation=reconciliation
    ).order_by('transaction_date')
    lines = _annotate_reconciliation_lines(list(lines_qs), statement_lines)

    cleared_count = sum(1 for line in lines if line.is_cleared)
    total_count   = len(lines)
    statement_count = statement_qs.count()

    if total_count == 0 and statement_count == 0:
            messages.info(request, (
                'No system transactions loaded for this reconciliation. '
                'Upload a bank statement (CSV/Excel) or create manual entries.'
            ))

    company_code = getattr(request, 'company_code', None)
    if not company_code and request.resolver_match:
        company_code = request.resolver_match.kwargs.get('company_code')
    pdf_url = get_company_redirect_url(
        request,
        'reconciliation_pdf',
        reconciliation_id=reconciliation.id,
    )

    return render(request, 'bank/reconciliation_working_screen.html', {
        'upload_url':           upload_url,
        'reconciliation':       reconciliation,
        'lines':                lines,
        'unmatched_statements': unmatched_statements,
        'statement_lines':      statement_lines,
        'has_unmatched':        has_unmatched,
        'cleared_count':        cleared_count,
        'total_count':          total_count,
        'company_code':         company_code,
        'reconciliation_pdf_url': pdf_url,
        **_get_bank_currency_context(request, company_db),
    })


# ─────────────────────────────────────────────────────────────
# PDF export for reconciliation
@login_required
def reconciliation_pdf_view(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_view_reconciliation(request.user)):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Bank Reconciliation',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    lines = list(
        BankReconciliationLine.objects.using(company_db)
        .filter(reconciliation=reconciliation)
        .order_by('transaction_date')
    )
    statement_qs = fetch_statement_lines(reconciliation, using_alias=company_db)
    unmatched_statements = list(
        statement_qs.filter(match_status='unmatched').order_by('statement_date')
    )

    import io
    import os
    import base64
    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image as RLImage

    # Register a Unicode-capable font so currency symbols render correctly.
    font_registered = False
    try:
        font_paths = [
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf'),
            'C:/Windows/Fonts/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Supplemental/DejaVuSans.ttf',
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                font_registered = True
                break
    except Exception:
        font_registered = False

    font_name = 'DejaVuSans' if font_registered else 'Helvetica'
    currency  = ''

    currency_context = _get_bank_currency_context(request, company_db)
    currency = currency_context.get('base_currency_symbol') or currency_context.get('base_currency_code') or currency

    def safe(val):
        return str(val or '').strip()

    def fmt(value):
        amt = Decimal(str(value or 0))
        prefix = '-' if amt < 0 else ''
        return f"{currency}{prefix}{abs(amt):,.2f}"

    # ── Document setup ────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f'Bank Reconciliation #{reconciliation.id}',
        author='LyraERP',
    )

    styles   = getSampleStyleSheet()
    elements = []

    # ── Paragraph styles ──────────────────────────────────────────────────────
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica-Bold',
    )
    meta_value_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#2c3e50'),
        fontName=font_name,
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#ffffff'),
        fontName='Helvetica-Bold',
    )
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#2c3e50'),
        fontName=font_name,
    )
    amount_style = ParagraphStyle(
        'Amount',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#2c3e50'),
        fontName=font_name,
        alignment=TA_RIGHT,
    )
    amount_red_style = ParagraphStyle(
        'AmountRed',
        parent=amount_style,
        textColor=colors.HexColor('#dc2626'),
    )
    amount_green_style = ParagraphStyle(
        'AmountGreen',
        parent=amount_style,
        textColor=colors.HexColor('#059669'),
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=6,
        spaceAfter=3,
    )

    # ── Company object — pull ALL fields directly from company_db ───────────────
    # company_db is the per-tenant DB alias; the Company record there has
    # the complete address, logo, GSTIN etc filled in during company setup.
    from company_settings.models import Company

    def _cf(obj, field):
        """Safe field getter; handles CountryField objects."""
        val = getattr(obj, field, None)
        if not val:
            return ''
        return safe(str(val))

    try:
        company = Company.objects.using(company_db).first()
    except Exception:
        company = None

    if company:
        company_name  = _cf(company, 'name')
        company_legal = _cf(company, 'legal_name')
        addr1         = _cf(company, 'address_line1')
        addr2         = _cf(company, 'address_line2')
        city          = _cf(company, 'city')
        state         = _cf(company, 'state')
        country       = _cf(company, 'country')
        postal        = _cf(company, 'postal_code')
        gstin         = _cf(company, 'tax_id')
        company_email = _cf(company, 'email')
    else:
        company_name  = ''
        company_legal = addr1 = addr2 = city = state = country = postal = gstin = company_email = ''

    # ── 1. HEADER — logo + company name left | badge right ──────────────────
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=0,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
    )
    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
    )

    show_logo = (
        company
        and getattr(company, 'show_logo_in_print_pdf', False)
        and getattr(company, 'logo_base64', None)
    )

    # Build left cell: logo (small, inline) + company name side by side
    if show_logo:
        logo_bytes = base64.b64decode(company.logo_base64)
        logo_img   = RLImage(io.BytesIO(logo_bytes), width=10 * mm, height=10 * mm)
        logo_img.hAlign = 'LEFT'
        # Nest logo + name into a small inner table so they sit on same line
        left_cell = Table(
            [[logo_img, Paragraph(f"<b>{company_name}</b>", title_style)]],
            colWidths=[12 * mm, 98 * mm],
        )
        left_cell.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
    else:
        left_cell = Paragraph(f"<b>{company_name}</b>", title_style)

    header_data = [[
        left_cell,
        Paragraph("BANK RECONCILIATION", badge_style),
    ]]
    header_table = Table(header_data, colWidths=[310, 210])
    header_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (1, 0), (1,  0),  'RIGHT'),
        ('LINEBELOW',     (0, 0), (-1, -1), 1.5, colors.HexColor('#e0e0e0')),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5 * mm))

    # ── 2. COMPANY INFO — name + address paragraph below header ───────────────
    company_header_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#555555'),
        fontName=font_name,
        leading=10,
        leftIndent=10,
    )

    _info_lines = []
    if company_legal: _info_lines.append(company_legal)
    if addr1:         _info_lines.append(addr1)
    if addr2:         _info_lines.append(addr2)
    _city_line = ', '.join(filter(None, [city, state, country, postal]))
    if _city_line:    _info_lines.append(_city_line)
    if gstin:         _info_lines.append(f"GSTIN: {gstin}")
    if company_email: _info_lines.append(company_email)

    company_info = (
        f"<font color='#2c3e50'><b>{company_name}</b></font><br/>"
        + (("<font size='6' color='#555555'>" + "<br/>".join(_info_lines) + "</font>") if _info_lines else "")
    )
    elements.append(Paragraph(company_info, company_header_style))
    elements.append(Spacer(1, 6 * mm))

    # ── 3. META INFO TABLE ────────────────────────────────────────────────────
    acc          = reconciliation.bank_account
    bank_name    = safe(acc.bank.bank_name) if acc and acc.bank else '—'
    account_no   = safe(acc.account_number) if acc else '—'
    period_start = reconciliation.start_date.strftime('%d/%m/%Y') if reconciliation.start_date else '—'
    period_end   = reconciliation.end_date.strftime('%d/%m/%Y')   if reconciliation.end_date   else '—'

    meta_data = [
        [
            Paragraph("<b>Bank</b>",           meta_label_style), Paragraph(bank_name,    meta_value_style),
            Paragraph("<b>Account No.</b>",    meta_label_style), Paragraph(account_no,   meta_value_style),
        ],
        [
            Paragraph("<b>Recon. ID</b>",      meta_label_style), Paragraph(f"#{reconciliation.id}", meta_value_style),
            Paragraph("<b>Status</b>",         meta_label_style), Paragraph(reconciliation.status,    meta_value_style),
        ],
        [
            Paragraph("<b>Period From</b>",    meta_label_style), Paragraph(period_start, meta_value_style),
            Paragraph("<b>Period To</b>",      meta_label_style), Paragraph(period_end,   meta_value_style),
        ],
        [
            Paragraph("<b>Prepared On</b>",    meta_label_style), Paragraph(date.today().strftime('%d/%m/%Y'), meta_value_style),
            Paragraph("<b>Reconciled On</b>",  meta_label_style),
            Paragraph(
                reconciliation.reconciled_date.strftime('%d/%m/%Y') if reconciliation.reconciled_date else '—',
                meta_value_style
            ),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[80, 185, 80, 175])
    meta_table.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), font_name),
        ('FONTSIZE',      (0, 0), (-1, -1), 7),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND',    (0, 0), (0, -1),  colors.HexColor('#f8f9fa')),
        ('BACKGROUND',    (2, 0), (2, -1),  colors.HexColor('#f8f9fa')),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 5 * mm))

    # ── 3. SUMMARY TABLE ─────────────────────────────────────────────────────
    diff       = Decimal(str(reconciliation.difference or 0))
    diff_color = colors.HexColor('#059669') if diff == 0 else colors.HexColor('#dc2626')
    diff_style = ParagraphStyle('DiffAmt', parent=amount_style, textColor=diff_color)

    summary_data = [[
        Paragraph("<b>Closing Balance</b>", label_style),
        Paragraph("<b>Cleared Amount</b>",  label_style),
        Paragraph("<b>Difference</b>",      label_style),
    ], [
        Paragraph(fmt(reconciliation.closing_balance), amount_style),
        Paragraph(fmt(reconciliation.cleared_amount),  amount_style),
        Paragraph(fmt(reconciliation.difference),      diff_style),
    ]]
    summary_table = Table(summary_data, colWidths=[173, 173, 174])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#2c3e50')),
        ('BACKGROUND',    (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('LINEWIDTH',     (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    # ── 4. SYSTEM TRANSACTIONS TABLE ──────────────────────────────────────────
    elements.append(Paragraph('System Transactions', section_style))

    cleared_count = sum(1 for l in lines if l.is_cleared)
    total_count   = len(lines)

    txn_data = [[
        Paragraph("<b>#</b>",           label_style),
        Paragraph("<b>Date</b>",        label_style),
        Paragraph("<b>Description</b>", label_style),
        Paragraph("<b>Reference</b>",   label_style),
        Paragraph("<b>Type</b>",        label_style),
        Paragraph("<b>Debit (Out)</b>", label_style),
        Paragraph("<b>Credit (In)</b>", label_style),
        Paragraph("<b>Cleared</b>",     label_style),
    ]]

    if lines:
        for idx, line in enumerate(lines, 1):
            debit_amt  = Decimal(str(line.debit_amount  or 0)) if hasattr(line, 'debit_amount')  else Decimal(0)
            credit_amt = Decimal(str(line.credit_amount or 0)) if hasattr(line, 'credit_amount') else Decimal(0)

            if not hasattr(line, 'debit_amount'):
                amt = Decimal(str(line.amount or 0))
                debit_amt  = abs(amt) if amt < 0 else Decimal(0)
                credit_amt = amt      if amt > 0 else Decimal(0)

            debit_cell  = Paragraph(f"{currency}{debit_amt:,.2f}",  amount_red_style)   if debit_amt  > 0 else Paragraph('—', value_style)
            credit_cell = Paragraph(f"{currency}{credit_amt:,.2f}", amount_green_style) if credit_amt > 0 else Paragraph('—', value_style)

            cleared_cell = Paragraph(
                "<font color='#059669'><b>✓</b></font>" if line.is_cleared else "<font color='#dc2626'>✗</font>",
                ParagraphStyle('CC', parent=value_style, alignment=TA_CENTER)
            )

            txn_data.append([
                Paragraph(str(idx), value_style),
                Paragraph(line.transaction_date.strftime('%d/%m/%Y'), value_style),
                Paragraph(safe(line.description) or '—', value_style),
                Paragraph(safe(line.reference)   or '—', value_style),
                Paragraph(line.get_transaction_type_display(), value_style),
                debit_cell,
                credit_cell,
                cleared_cell,
            ])
    else:
        txn_data.append([
            Paragraph('No system transactions recorded for this period.', value_style),
            '', '', '', '', '', '', '',
        ])

    txn_table = Table(txn_data, colWidths=[18, 52, 145, 70, 60, 60, 60, 55])
    txn_style = TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), font_name),
        ('FONTSIZE',      (0, 0), (-1, -1), 7),
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.HexColor('#ffffff')),
        ('ALIGN',         (0, 0), (0, -1),  'CENTER'),
        ('ALIGN',         (5, 1), (7, -1),  'RIGHT'),
        ('ALIGN',         (7, 1), (7, -1),  'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('LINEWIDTH',     (0, 0), (-1, -1), 0.5),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
    ])

    for row_idx, line in enumerate(lines, 1):
        if line.is_cleared:
            txn_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f3f4f6'))

    txn_table.setStyle(txn_style)
    elements.append(txn_table)

    elements.append(
        Paragraph(
            f"<font color='#6b7280'>{cleared_count} of {total_count} transactions cleared</font>",
            ParagraphStyle('ClearedNote', parent=styles['Normal'], fontSize=7,
                           fontName=font_name, alignment=TA_RIGHT, spaceBefore=3),
        )
    )
    elements.append(Spacer(1, 5 * mm))

    # ── 5. UNMATCHED BANK STATEMENT ENTRIES ───────────────────────────────────
    elements.append(Paragraph('Unmatched Bank Statement Entries', section_style))

    if unmatched_statements:
        stmt_data = [[
            Paragraph("<b>#</b>",           label_style),
            Paragraph("<b>Date</b>",        label_style),
            Paragraph("<b>Description</b>", label_style),
            Paragraph("<b>Reference</b>",   label_style),
            Paragraph("<b>Debit (Out)</b>", label_style),
            Paragraph("<b>Credit (In)</b>", label_style),
        ]]

        for idx, stmt in enumerate(unmatched_statements, 1):
            debit_amt  = Decimal(str(stmt.debit_amount  or 0)) if hasattr(stmt, 'debit_amount')  else Decimal(0)
            credit_amt = Decimal(str(stmt.credit_amount or 0)) if hasattr(stmt, 'credit_amount') else Decimal(0)

            if not hasattr(stmt, 'debit_amount'):
                amt = Decimal(str(stmt.amount or 0))
                debit_amt  = abs(amt) if amt < 0 else Decimal(0)
                credit_amt = amt      if amt > 0 else Decimal(0)

            stmt_data.append([
                Paragraph(str(idx), value_style),
                Paragraph(stmt.statement_date.strftime('%d/%m/%Y'), value_style),
                Paragraph(safe(stmt.description) or '—', value_style),
                Paragraph(safe(stmt.reference)   or '—', value_style),
                Paragraph(f"{currency}{debit_amt:,.2f}",  amount_red_style)   if debit_amt  > 0 else Paragraph('—', value_style),
                Paragraph(f"{currency}{credit_amt:,.2f}", amount_green_style) if credit_amt > 0 else Paragraph('—', value_style),
            ])

        stmt_table = Table(stmt_data, colWidths=[18, 62, 195, 90, 67, 88])
        stmt_table.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, -1), font_name),
            ('FONTSIZE',      (0, 0), (-1, -1), 7),
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.HexColor('#ffffff')),
            ('ALIGN',         (0, 0), (0, -1),  'CENTER'),
            ('ALIGN',         (4, 1), (5, -1),  'RIGHT'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('LINEWIDTH',     (0, 0), (-1, -1), 0.5),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#fffbeb')]),
        ]))
        elements.append(stmt_table)

    else:
        matched_banner_data = [[
            Paragraph(
                "<font color='#059669'><b>✓  All Statement Lines Matched</b></font><br/>"
                "<font size='6' color='#6b7280'>Every uploaded bank statement entry has been successfully "
                "matched to a system transaction. No unmatched lines remain.</font>",
                ParagraphStyle(
                    'MatchedBanner', parent=styles['Normal'],
                    fontSize=8, fontName=font_name, leading=13, leftIndent=4,
                ),
            )
        ]]
        matched_banner = Table(matched_banner_data, colWidths=[520])
        matched_banner.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#ecfdf5')),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#9ca3af')),
        ]))
        elements.append(matched_banner)

    elements.append(Spacer(1, 5 * mm))

    # ── 6. TOTALS SECTION ─────────────────────────────────────────────────────
    totals_label_style = ParagraphStyle(
        'TotalLabel', parent=styles['Normal'], fontSize=7,
        textColor=colors.HexColor('#2c3e50'), fontName='Helvetica', alignment=TA_RIGHT,
    )
    grand_total_label_style = ParagraphStyle(
        'GrandTotalLabel', parent=styles['Normal'], fontSize=8,
        fontName=font_name,
        textColor=colors.HexColor('#ffffff'),
    )
    grand_total_value_style = ParagraphStyle(
        'GrandTotalValue', parent=styles['Normal'], fontSize=8,
        fontName=font_name,
        textColor=colors.HexColor('#ffffff'),
        alignment=TA_RIGHT,
    )

    totals_data = [
        [Paragraph("Closing Balance (Bank Statement)", totals_label_style),
         Paragraph(fmt(reconciliation.closing_balance), amount_style)],
        [Paragraph("Cleared Amount (Ticked Transactions)", totals_label_style),
         Paragraph(fmt(reconciliation.cleared_amount), amount_style)],
        [Paragraph(f"<b>Difference — must reach {currency}0.00</b>", grand_total_label_style),
         Paragraph(f"<b>{fmt(reconciliation.difference)}</b>", grand_total_value_style)],
    ]
    totals_table = Table(totals_data, colWidths=[371, 149])
    totals_table.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), font_name),
        ('ALIGN',         (0, 0), (0, -1),  'RIGHT'),
        ('ALIGN',         (1, 0), (1, -1),  'RIGHT'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('BACKGROUND',    (0, 0), (-1, -2), colors.HexColor('#ffffff')),
        ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',     (0, -1), (0, -1),  colors.HexColor('#ffffff')),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('LINEWIDTH',     (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 5 * mm))

    # ── 7. NOTES & AUTHORISED SIGNATORY ──────────────────────────────────────
    status_note = (
        "This reconciliation is <b>locked</b> and has been finalized."
        if reconciliation.is_reconciled
        else f"This reconciliation is <b>in progress</b>. Difference must reach {currency}0.00 before completion."
    )
    bottom_data = [[
        Paragraph(
            f"<b>Notes / Status</b><br/><font size='6'>{status_note}</font>",
            value_style,
        ),
        Paragraph(
            f"<b>Authorised Signatory</b><br/><br/>For {company_name}",
            value_style,
        ),
    ]]
    bottom_table = Table(bottom_data, colWidths=[330, 190])
    bottom_table.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), font_name),
        ('FONTSIZE',      (0, 0), (-1, -1), 7),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('GRID',          (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(bottom_table)

    # ── 8. FOOTER ─────────────────────────────────────────────────────────────
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 6)
        canvas.setFillColor(colors.grey)
        canvas.drawString(30, 20, 'POWERED BY LyraERP')
        page_num = canvas.getPageNumber()
        canvas.drawRightString(570, 20, f'Page {page_num}')
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    download_mode = request.GET.get('download', '').lower() in ('1', 'true', 'yes', 'download')
    disposition   = 'attachment' if download_mode else 'inline'
    response['Content-Disposition'] = (
        f'{disposition}; filename="bank-reconciliation-{reconciliation.id}.pdf"'
    )
    return response


#  Bank Rules UI
# ─────────────────────────────────────────────────────────────

@login_required
def bank_rules_list(request, account_id):
    if not can_view_banking(request.user):
        return render(request, 'site_blocked.html', {
            'restriction_type': 'permission',
            'blocked_module': 'Banking',
            'company_code': getattr(request, 'company_code', None),
        }, status=403)
    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )
    rules = BankRule.objects.using(company_db).filter(bank_account=account).order_by('-created_at')
    return render(request, 'bank/bank_rules_list.html', {
        'account': account,
        'rules': rules,
    })


@login_required
def bank_rule_create(request, account_id):
    if not can_create_banking(request.user):
        messages.error(request, 'You do not have permission to create bank rules.')
        return redirect_with_company(request, 'bank_rules_list', account_id=account_id)
    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )
    if request.method == 'POST':
        form = BankRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.bank_account = account
            rule.save(using=company_db)
            messages.success(request, 'Bank rule created.')
            return redirect_with_company(request, 'bank_rules_list', account.id)
    else:
        form = BankRuleForm()
    return render(request, 'bank/bank_rule_form.html', {
        'account': account,
        'form': form,
        'action': 'Create',
        **_get_bank_currency_context(request, company_db),
    })


@login_required
def bank_rule_edit(request, account_id, rule_id):
    if not can_edit_banking(request.user):
        messages.error(request, 'You do not have permission to edit bank rules.')
        return redirect_with_company(request, 'bank_rules_list', account_id=account_id)
    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )
    rule = get_object_or_404(
        BankRule.objects.using(company_db), id=rule_id, bank_account=account
    )
    if request.method == 'POST':
        form = BankRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank rule updated.')
            return redirect_with_company(request, 'bank_rules_list', account.id)
    else:
        form = BankRuleForm(instance=rule)
    return render(request, 'bank/bank_rule_form.html', {
        'account': account,
        'form': form,
        'action': 'Edit',
        **_get_bank_currency_context(request, company_db),
    })


@login_required
@require_http_methods(['POST'])
def bank_rule_delete(request, account_id, rule_id):
    if not can_delete_banking(request.user):
        messages.error(request, 'You do not have permission to delete bank rules.')
        return redirect_with_company(request, 'bank_rules_list', account_id=account_id)
    company_db = _get_company_db_alias(request)
    account = get_object_or_404(
        CompanyBankAccount.objects.using(company_db), id=account_id, status=True
    )
    rule = get_object_or_404(
        BankRule.objects.using(company_db), id=rule_id, bank_account=account
    )
    rule.delete()
    messages.success(request, 'Bank rule deleted.')
    return redirect_with_company(request, 'bank_rules_list', account.id)


# ─────────────────────────────────────────────────────────────
#  AJAX — Toggle transaction cleared
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def reconciliation_toggle_transaction(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_edit_reconciliation(request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    if reconciliation.is_locked():
        return JsonResponse({
            'success': False,
            'error': 'This reconciliation is locked and cannot be modified.'
        }, status=400)

    try:
        data       = json.loads(request.body)
        line_id    = data.get('line_id')
        is_cleared = bool(data.get('is_cleared', False))

        line = get_object_or_404(
            BankReconciliationLine.objects.using(company_db),
            id=line_id, reconciliation=reconciliation
        )
        line.is_cleared = is_cleared
        line.save(using=company_db, update_fields=['is_cleared'])

        totals = update_reconciliation_totals(reconciliation)

        cleared_count = BankReconciliationLine.objects.using(company_db).filter(
            reconciliation=reconciliation, is_cleared=True
        ).count()
        total_count = BankReconciliationLine.objects.using(company_db).filter(
            reconciliation=reconciliation
        ).count()

        return JsonResponse({
            'success':        True,
            'cleared_amount': str(totals['cleared_amount']),
            'difference':     str(totals['difference']),
            'can_reconcile':  totals['can_reconcile'],
            'cleared_count':  cleared_count,
            'total_count':    total_count,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────
#  AJAX — Complete reconciliation
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def reconciliation_complete(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_edit_reconciliation(request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    update_reconciliation_totals(reconciliation)
    reconciliation.refresh_from_db(using=company_db)

    if reconciliation.difference != Decimal('0.00'):
        currency_context = _get_bank_currency_context(request, company_db)
        currency = currency_context.get('base_currency_symbol') or currency_context.get('base_currency_code') or ''
        return JsonResponse({
            'success': False,
            'error':   f'Difference must be {currency}0.00 before reconciling. Current difference: {currency}{reconciliation.difference}',
        }, status=400)

    reconciliation.status          = 'Reconciled'
    reconciliation.reconciled_date = date.today()
    reconciliation.save(using=company_db, update_fields=['status', 'reconciled_date'])

    return JsonResponse({
        'success':         True,
        'message':         'Reconciliation completed successfully.',
        'reconciled_date': reconciliation.reconciled_date.strftime('%d/%m/%Y'),
        'redirect_url':    get_company_redirect_url(
            request,
            'reconciliation_list',
            account_id=reconciliation.bank_account_id,
        ),
    })


# ─────────────────────────────────────────────────────────────
#  AJAX — Undo reconciliation
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def reconciliation_undo(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_edit_reconciliation(request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    newest = BankReconciliation.objects.using(company_db).filter(
        bank_account=reconciliation.bank_account,
        status='Reconciled',
    ).order_by('-end_date').first()

    if newest and newest.id != reconciliation.id:
        return JsonResponse({
            'success': False,
            'error': (
                'To undo this reconciliation, you must first undo all '
                'reconciliations after this period.'
            ),
        }, status=400)

    BankReconciliationLine.objects.using(company_db).filter(
        reconciliation=reconciliation
    ).update(is_cleared=False, auto_matched=False)

    fetch_statement_lines(reconciliation, using_alias=company_db).update(
        match_status='unmatched', matched_transaction_id=None
    )

    reconciliation.status          = 'In Progress'
    reconciliation.reconciled_date = None
    reconciliation.save(using=company_db, update_fields=['status', 'reconciled_date'])

    update_reconciliation_totals(reconciliation)

    return JsonResponse({
        'success':      True,
        'message':      'Reconciliation undone successfully.',
        'redirect_url': get_company_redirect_url(
            request,
            'reconciliation_working_screen',
            reconciliation_id=reconciliation_id,
        ),
    })


# ─────────────────────────────────────────────────────────────
#  AJAX — Delete reconciliation
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def reconciliation_delete(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_delete_reconciliation(request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    newest = BankReconciliation.objects.using(company_db).filter(
        bank_account=reconciliation.bank_account
    ).order_by('-end_date').first()

    if newest and newest.id != reconciliation.id:
        return JsonResponse({
            'success': False,
            'error': 'You can only delete the most recent reconciliation.',
        }, status=400)

    account_id = reconciliation.bank_account_id
    reconciliation.delete(using=company_db)

    return JsonResponse({
        'success':      True,
        'message':      'Reconciliation deleted.',
        'redirect_url': get_company_redirect_url(
            request,
            'reconciliation_list',
            account_id=account_id,
        ),
    })


# ─────────────────────────────────────────────────────────────
#  AJAX — Create manual entry from unmatched statement line
# ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def create_manual_entry_from_statement(request, reconciliation_id):
    if not (getattr(request.user, 'is_superuser', False) or can_create_reconciliation(request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    reconciliation, company_db = _load_reconciliation(request, reconciliation_id)

    if reconciliation.is_locked():
        return JsonResponse({'success': False, 'error': 'Reconciliation is locked.'}, status=400)

    try:
        data = json.loads(request.body)
        stmt_line = get_object_or_404(
            BankStatementLine.objects.using(company_db),
            id=data['statement_line_id'], reconciliation=reconciliation
        )

        offset_id = data.get('offset_account_id')
        if offset_id is not None and offset_id != '':
            try:
                offset_id = int(offset_id)
            except (TypeError, ValueError):
                offset_id = None
        else:
            offset_id = None

        with transaction.atomic(using=company_db):
            manual_line, _je = create_posted_journal_for_statement_line(
                reconciliation,
                stmt_line,
                request.user,
                company_db,
                offset_account_id=offset_id,
            )
        # match status is updated inside create_posted_journal_for_statement_line

        totals = update_reconciliation_totals(reconciliation)

        cleared_count = BankReconciliationLine.objects.using(company_db).filter(
            reconciliation=reconciliation, is_cleared=True
        ).count()
        total_count = BankReconciliationLine.objects.using(company_db).filter(
            reconciliation=reconciliation
        ).count()

        return JsonResponse({
            'success':        True,
            'message':        'Journal entry posted; it appears under System Transactions as cleared.',
            'line_id':        manual_line.id,
            'cleared_amount': str(totals['cleared_amount']),
            'difference':     str(totals['difference']),
            'can_reconcile':  totals['can_reconcile'],
            'cleared_count':  cleared_count,
            'total_count':    total_count,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
