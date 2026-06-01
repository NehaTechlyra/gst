"""
Bank Reconciliation Utilities - CSV/Excel/PDF Parsing, Auto-Matching, Transaction Loading
Matches specification for Zoho Books-style bank reconciliation
"""
import csv
import io
from decimal import Decimal
from datetime import datetime, date, timedelta
from pathlib import Path
from django.db.models import Sum, Q
from .models import (
    BankReconciliation, BankReconciliationLine, BankStatementLine, BankRule
)
import re
from journal.models import JournalEntry, JournalLine
from chart_of_accounts.models import ChartOfAccounts
from company_settings.utils import ensure_bank_chart_account


class BankStatementCSVParser:
    """Parse bank statement CSV files with flexible column detection"""

    SUPPORTED_FORMATS = {
        'date': ['statement_date', 'trans_date', 'date', 'transaction_date', 'posting_date'],
        'description': ['description', 'desc', 'narration', 'particulars', 'memo'],
        'debit': ['debit', 'withdrawal', 'outflow', 'dr', 'amount_out', 'debits'],
        'credit': ['credit', 'deposit', 'inflow', 'cr', 'amount_in', 'credits'],
        'amount': ['amount', 'transaction_amount', 'amt', 'value', 'change'],
        'reference': ['reference', 'ref', 'cheque_no', 'cheque_number', 'ref_num', 'reference#'],
    }

    DEFAULT_DATE_FORMATS = [
        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y',
        '%d %b %Y', '%d %B %Y', '%Y/%m/%d',
    ]

    def __init__(self, file):
        self.file = file
        self.rows = []
        self.errors = []

    def parse(self):
        """Parse CSV file and return list of transaction dicts"""
        try:
            if hasattr(self.file, 'read'):
                file_content = self.file.read()
            else:
                file_content = self.file.getvalue()

            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8-sig')  # handles BOM

            file_obj = io.StringIO(file_content)
            reader = csv.DictReader(file_obj)

            if not reader.fieldnames:
                self.errors.append("CSV file is empty or has no headers.")
                return self.rows

            headers = {h.lower().strip(): h for h in reader.fieldnames}
            col_mapping = self._detect_columns(headers)

            if not col_mapping.get('date'):
                self.errors.append(
                    "CSV must have a Date column. "
                    "Accepted names: date, statement_date, trans_date, transaction_date, posting_date."
                )
                return self.rows

            if not (col_mapping.get('debit') or col_mapping.get('credit') or col_mapping.get('amount')):
                self.errors.append(
                    "CSV must have at least one amount column. "
                    "Accepted names: debit/credit, debits/credits, amount, withdrawal/deposit."
                )
                return self.rows

            for idx, row in enumerate(reader, start=2):
                try:
                    transaction = self._parse_row(row, col_mapping, idx)
                    if transaction:
                        self.rows.append(transaction)
                except ValueError as e:
                    self.errors.append(f"Row {idx}: {str(e)}")

            return self.rows

        except Exception as e:
            self.errors.append(f"CSV parsing failed: {str(e)}")
            return self.rows

    def _detect_columns(self, headers):
        mapping = {}
        for field, aliases in self.SUPPORTED_FORMATS.items():
            for lower_header, original_header in headers.items():
                for alias in aliases:
                    pattern = self._alias_pattern(alias)
                    if pattern.search(lower_header):
                        mapping[field] = original_header
                        break
                if field in mapping:
                    break
        return mapping

    def _alias_pattern(self, alias):
        normalized = alias.lower()
        parts = [part for part in re.split(r'[\s_\-#]+', normalized) if part]
        if not parts:
            parts = [normalized]
        joined = r'[\s_\-#]*'.join(re.escape(part) for part in parts)
        return re.compile(rf'(?<![a-z0-9]){joined}s?(?![a-z0-9])')

    def _parse_row(self, row, col_mapping, row_num):
        date_str = row.get(col_mapping.get('date'), '').strip()
        description = row.get(col_mapping.get('description'), '').strip() if col_mapping.get('description') else ''
        debit_str = row.get(col_mapping.get('debit'), '').strip() if col_mapping.get('debit') else ''
        credit_str = row.get(col_mapping.get('credit'), '').strip() if col_mapping.get('credit') else ''
        amount_column = col_mapping.get('amount')
        amount_str = row.get(amount_column, '').strip() if amount_column else ''
        reference = row.get(col_mapping.get('reference'), '').strip() if col_mapping.get('reference') else ''

        # Skip blank rows
        if not date_str and not (debit_str or credit_str or amount_str):
            return None

        # Skip summary rows
        summary_markers = {'subtotal', 'total', 'difference', 'balance', 'opening', 'closing'}
        if not date_str and description:
            if any(marker in description.lower() for marker in summary_markers):
                return None

        transaction_date = self._parse_date(date_str)
        if not transaction_date:
            if not date_str:
                return None
            raise ValueError(f"Invalid date format: '{date_str}'. Supported: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD")

        debit_amount = self._parse_amount(debit_str) if debit_str else Decimal('0.00')
        credit_amount = self._parse_amount(credit_str) if credit_str else Decimal('0.00')

        if not debit_str and not credit_str and amount_str:
            amount_value = self._parse_amount(amount_str)
            if amount_value > 0:
                credit_amount = amount_value
            elif amount_value < 0:
                debit_amount = -amount_value

        if debit_amount == 0 and credit_amount == 0:
            return None

        return {
            'statement_date': transaction_date,
            'description': description or 'No description',
            'reference': reference,
            'debit_amount': debit_amount,
            'credit_amount': credit_amount,
        }

    def _parse_date(self, date_str):
        if not date_str:
            return None
        date_str = date_str.strip()
        for fmt in self.DEFAULT_DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_amount(self, amount_str):
        try:
            cleaned = re.sub(r'[₹$€£¥,\s]', '', amount_str)
            return Decimal(cleaned) if cleaned else Decimal('0.00')
        except Exception:
            return Decimal('0.00')


# ─────────────────────────────────────────────────────────────
#  File Conversion Helpers
# ─────────────────────────────────────────────────────────────

def _convert_excel_to_csv_text(content, extension):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    rows_written = 0

    if extension == '.xlsx':
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise ValueError("Excel uploads require the 'openpyxl' package. Install: pip install openpyxl") from exc

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        for row in sheet.iter_rows(values_only=True):
            normalized = [_normalize_excel_value(value) for value in row]
            if not any(normalized):
                continue
            writer.writerow(normalized)
            rows_written += 1
    else:
        try:
            import xlrd
        except ImportError as exc:
            raise ValueError("XLS uploads require the 'xlrd' package. Install: pip install xlrd") from exc

        book = xlrd.open_workbook(file_contents=content)
        sheet = book.sheet_by_index(0)
        for row_idx in range(sheet.nrows):
            normalized = [_normalize_xlrd_cell(cell, book.datemode) for cell in sheet.row(row_idx)]
            if not any(normalized):
                continue
            writer.writerow(normalized)
            rows_written += 1

    if rows_written == 0:
        raise ValueError("Excel file contains no usable rows.")

    return buffer.getvalue()


def _convert_pdf_to_csv_text(content):
    """
    Extract tabular data from a PDF bank statement and return as CSV text.
    Requires: pip install pdfplumber
    """
    try:
        import pdfplumber
    except ImportError:
        raise ValueError(
            "PDF parsing requires the 'pdfplumber' package. Install it with: pip install pdfplumber"
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    rows_written = 0

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Try structured table extraction first
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            cleaned = [
                                str(cell).strip().replace('\n', ' ') if cell is not None else ''
                                for cell in row
                            ]
                            if not any(cleaned):
                                continue
                            writer.writerow(cleaned)
                            rows_written += 1
                else:
                    # Fallback: extract raw text and split on whitespace gaps
                    text = page.extract_text()
                    if not text:
                        continue
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                        if len(parts) >= 2:
                            writer.writerow(parts)
                            rows_written += 1

    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")

    if rows_written == 0:
        return None

    return buffer.getvalue()


def _normalize_excel_value(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    return str(value).strip()


def _normalize_xlrd_cell(cell, datemode):
    import xlrd
    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return ''
    if cell.ctype == xlrd.XL_CELL_DATE:
        dt = xlrd.xldate_as_datetime(cell.value, datemode)
        return dt.strftime('%d/%m/%Y')
    return str(cell.value).strip()


# ─────────────────────────────────────────────────────────────
#  Main Parse Entry Point
# ─────────────────────────────────────────────────────────────

def parse_bank_statement_file(uploaded_file):
    """
    Parse CSV, Excel (.xls/.xlsx), or PDF bank statement uploads.
    Returns (parsed_rows, errors).
    """
    ext = Path(uploaded_file.name).suffix.lower()

    if ext == '.csv':
        parser = BankStatementCSVParser(uploaded_file)
        return parser.parse(), parser.errors

    if ext in ('.xls', '.xlsx'):
        content = uploaded_file.read()
        csv_text = _convert_excel_to_csv_text(content, ext)
        parser = BankStatementCSVParser(io.StringIO(csv_text))
        return parser.parse(), parser.errors

    if ext == '.pdf':
        content = uploaded_file.read()
        csv_text = _convert_pdf_to_csv_text(content)
        if not csv_text:
            raise ValueError(
                "Could not extract tabular data from this PDF. "
                "Please upload a CSV or Excel version of your bank statement instead."
            )
        parser = BankStatementCSVParser(io.StringIO(csv_text))
        return parser.parse(), parser.errors

    raise ValueError(
        f"Unsupported file type '{ext}'. Please upload a CSV, Excel (.xlsx/.xls), or PDF file."
    )


# ─────────────────────────────────────────────────────────────
#  DB Alias Helper
# ─────────────────────────────────────────────────────────────

def _get_reconciliation_db_alias(reconciliation):
    """Return the database alias where this reconciliation lives."""
    alias = getattr(getattr(reconciliation, '_state', None), 'db', None)
    if alias:
        return alias
    try:
        from Lyraerp.utils.thread_locals import get_current_db
        current = get_current_db()
        if current:
            return current
    except Exception:
        pass
    return 'default'


# ─────────────────────────────────────────────────────────────
#  Statement Line Helpers
# ─────────────────────────────────────────────────────────────

def fetch_statement_lines(reconciliation, *, using_alias=None):
    alias = using_alias or _get_reconciliation_db_alias(reconciliation)
    return BankStatementLine.objects.using(alias).filter(reconciliation=reconciliation)


def fetch_unmatched_statements(reconciliation, *, using_alias=None):
    return fetch_statement_lines(reconciliation, using_alias=using_alias).filter(match_status='unmatched')


def create_statement_entries_from_csv(reconciliation, parsed_entries, using_alias=None):
    """
    Create BankStatementLine records from parsed data.
    Returns dict with creation results.
    """
    created = []
    errors = []

    db_alias = using_alias or _get_reconciliation_db_alias(reconciliation)
    manager = BankStatementLine.objects.using(db_alias)
    bank_account_id = reconciliation.bank_account_id

    for entry_data in parsed_entries:
        try:
            line = manager.create(
                bank_account_id=bank_account_id,
                reconciliation=reconciliation,
                statement_date=entry_data['statement_date'],
                description=entry_data['description'],
                reference=entry_data.get('reference', ''),
                debit_amount=entry_data['debit_amount'],
                credit_amount=entry_data['credit_amount'],
                match_status='unmatched',
            )
            created.append(line)
        except Exception as e:
            errors.append(f"Error creating statement line: {str(e)}")

    return {
        'created': created,
        'count': len(created),
        'errors': errors,
    }


# ─────────────────────────────────────────────────────────────
#  Auto-Match Amount Helper
# ─────────────────────────────────────────────────────────────

def _stmt_matches_recon(stmt_line, recon_line, tolerance=Decimal('0.00')):
    """
    Direction-aware amount comparison.

    A CSV credit (money IN)  → journal DEBITS  the bank ledger  (debit_amount > 0)
    A CSV debit  (money OUT) → journal CREDITS the bank ledger  (credit_amount > 0)

    Using the raw .amount property on both sides fails because
    BankStatementLine.amount returns -credit_amount for credits,
    while BankReconciliationLine.amount returns +debit_amount for the
    matching bank-side journal line — so they are opposite in sign.
    """
    stmt_credit = stmt_line.credit_amount or Decimal('0.00')
    stmt_debit = stmt_line.debit_amount or Decimal('0.00')
    recon_debit = recon_line.debit_amount or Decimal('0.00')
    recon_credit = recon_line.credit_amount or Decimal('0.00')

    def close(a, b):
        return abs(a - b) <= tolerance

    if stmt_credit > 0:
        # preferred: credit -> debit (money in should debit bank)
        if recon_debit > 0 and close(stmt_credit, recon_debit):
            return True
        # allow same-side match for existing journals that record the bank leg as credit
        if recon_credit > 0 and close(stmt_credit, recon_credit):
            return True

    if stmt_debit > 0:
        # preferred: debit -> credit (money out should credit bank)
        if recon_credit > 0 and close(stmt_debit, recon_credit):
            return True
        # allow same-side match where bank entries are stored as debit amounts
        if recon_debit > 0 and close(stmt_debit, recon_debit):
            return True

    return False

def _persist_statement_match(stmt_line, recon_line, status, *, auto_matched=True, using_alias=None):
    alias = using_alias or _get_reconciliation_db_alias(stmt_line.reconciliation)

    BankStatementLine.objects.using(alias).filter(pk=stmt_line.pk).update(
        match_status=status,
        matched_transaction_id=recon_line.id,
    )
    stmt_line.match_status = status
    stmt_line.matched_transaction_id = recon_line.id

    BankReconciliationLine.objects.using(alias).filter(pk=recon_line.pk).update(
        auto_matched=auto_matched,
        is_cleared=True,
    )
    recon_line.auto_matched = auto_matched
    recon_line.is_cleared = True



# ─────────────────────────────────────────────────────────────
#  Auto Matcher
# ─────────────────────────────────────────────────────────────

DEFAULT_DATE_TOLERANCE_DAYS = 2


class ReconciliationAutoMatcher:
    """Auto-match bank statement lines to system transactions"""

    def __init__(self, reconciliation, using_alias=None):
        self.reconciliation = reconciliation
        self.using_alias = using_alias or _get_reconciliation_db_alias(reconciliation)

    def _recon_line_qs(self):
        return BankReconciliationLine.objects.using(self.using_alias).filter(
            reconciliation=self.reconciliation
        )

    def _do_match(self, stmt_line, recon_line, status, *, auto_matched=True):
        """
        Persist the match on both sides using direct queryset .update() calls.
        This avoids stale in-memory ORM object state causing silent save failures.
        """
        _persist_statement_match(
            stmt_line,
            recon_line,
            status,
            auto_matched=auto_matched,
            using_alias=self.using_alias,
        )

    def auto_match_all(self):
        matched_count = 0
        # Evaluate to list immediately — prevents queryset re-evaluation during
        # iteration after _do_match modifies match_status on these same rows
        statement_lines = list(
            fetch_unmatched_statements(self.reconciliation, using_alias=self.using_alias)
        )
        for stmt_line in statement_lines:
            if self.auto_match_line(stmt_line):
                matched_count += 1
        return matched_count

    def auto_match_line(self, stmt_line):
        # ── Try bank rules first ──
        rules = BankRule.objects.using(self.using_alias).filter(
            bank_account=self.reconciliation.bank_account, active=True, auto_match=True
        )
        for rule in rules:
            try:
                if not rule.pattern:
                    continue
                if not re.search(rule.pattern, (stmt_line.description or ''), re.IGNORECASE):
                    continue

                start_dt = stmt_line.statement_date - timedelta(days=rule.date_window)
                end_dt   = stmt_line.statement_date + timedelta(days=rule.date_window)

                candidates = self._recon_line_qs().filter(
                    transaction_date__range=(start_dt, end_dt)
                ).exclude(auto_matched=True)

                for cand in candidates:
                    if _stmt_matches_recon(stmt_line, cand, rule.amount_tolerance or Decimal('0.00')):
                        self._do_match(stmt_line, cand, 'auto_matched')
                        return True
            except Exception:
                continue

        # ── Reference match ──
        stmt_ref = (stmt_line.reference or '').strip()
        if stmt_ref:
            ref_candidates = self._recon_line_qs().filter(
                reference__iexact=stmt_ref,
            ).exclude(auto_matched=True)
            for recon_line in ref_candidates:
                if _stmt_matches_recon(stmt_line, recon_line):
                    self._do_match(stmt_line, recon_line, 'auto_matched')
                    return True

        # ── Fallback: exact date + direction-aware amount ──
        date_min = stmt_line.statement_date - timedelta(days=DEFAULT_DATE_TOLERANCE_DAYS)
        date_max = stmt_line.statement_date + timedelta(days=DEFAULT_DATE_TOLERANCE_DAYS)
        recon_lines = self._recon_line_qs().filter(
            transaction_date__range=(date_min, date_max),
        ).exclude(auto_matched=True)

        for recon_line in recon_lines:
            if _stmt_matches_recon(stmt_line, recon_line):
                self._do_match(stmt_line, recon_line, 'auto_matched')
                return True

        return False


# ─────────────────────────────────────────────────────────────
#  Transaction Loader
# ─────────────────────────────────────────────────────────────

class TransactionLoader:
    """Load system transactions into reconciliation"""

    @staticmethod
    def load_journal_entries(reconciliation, using_alias=None):
        count = 0
        alias = using_alias or _get_reconciliation_db_alias(reconciliation)

        chart_account = reconciliation.bank_account.chart_account or ensure_bank_chart_account(
            reconciliation.bank_account
        )
        if not chart_account:
            print(
                f"Skipping journal load for reconciliation #{reconciliation.id} "
                f"— bank account {reconciliation.bank_account} has no chart account."
            )
            return count

        journal_lines = JournalLine.objects.using(alias).filter(
            account=chart_account,
            journal__date__range=[reconciliation.start_date, reconciliation.end_date],
            status=True,
            journal__status='posted',
        ).select_related('journal')

        for line in journal_lines:
            if line.debit == Decimal('0.00') and line.credit == Decimal('0.00'):
                continue

            exists = BankReconciliationLine.objects.using(alias).filter(
                reconciliation=reconciliation,
                transaction_id=line.id,
                transaction_type='journal',
            ).exists()

            if exists:
                continue

            BankReconciliationLine.objects.using(alias).create(
                reconciliation=reconciliation,
                transaction_id=line.id,
                transaction_type='journal',
                transaction_date=line.journal.date,
                description=line.description or line.journal.description or '',
                reference=line.journal.reference or '',
                debit_amount=line.debit,
                credit_amount=line.credit,
                is_cleared=False,
                auto_matched=False,
            )
            count += 1

        return count


# ─────────────────────────────────────────────────────────────
#  Totals
# ─────────────────────────────────────────────────────────────

def calculate_cleared_amount(reconciliation):
    """Calculate net cleared amount from ticked transaction lines"""
    alias = _get_reconciliation_db_alias(reconciliation)
    cleared_lines = BankReconciliationLine.objects.using(alias).filter(
        reconciliation=reconciliation, is_cleared=True
    )
    total_debit = cleared_lines.aggregate(Sum('debit_amount'))['debit_amount__sum'] or Decimal('0.00')
    total_credit = cleared_lines.aggregate(Sum('credit_amount'))['credit_amount__sum'] or Decimal('0.00')
    return total_debit - total_credit


def update_reconciliation_totals(reconciliation):
    """Update cleared_amount and difference on reconciliation, saving to correct DB."""
    cleared_amount = calculate_cleared_amount(reconciliation)
    difference = reconciliation.closing_balance - cleared_amount
    reconciliation.cleared_amount = cleared_amount
    reconciliation.difference = difference
    alias = _get_reconciliation_db_alias(reconciliation)
    reconciliation.save(using=alias)
    return {
        'cleared_amount': cleared_amount,
        'difference': difference,
        'can_reconcile': difference == Decimal('0.00'),
    }


# ─────────────────────────────────────────────────────────────
#  Manual Journal Entry Creation
# ─────────────────────────────────────────────────────────────

def _next_journal_entry_number(using_alias):
    highest = 0
    for entry in JournalEntry.objects.using(using_alias).filter(
        entry_number__startswith='JV-'
    ).only('entry_number'):
        try:
            num = int(entry.entry_number.split('-')[1])
            if num > highest:
                highest = num
        except (IndexError, ValueError):
            continue
    return f'JV-{str(highest + 1).zfill(5)}'


def _first_leaf_account_under(using_alias, name_substr, exclude_pks=None):
    exclude_pks = exclude_pks or set()
    root = ChartOfAccounts.objects.using(using_alias).filter(
        name__icontains=name_substr
    ).order_by('code').first()
    if not root:
        return None
    stack = [root]
    while stack:
        node = stack.pop()
        if node.pk in exclude_pks:
            continue
        children = list(
            ChartOfAccounts.objects.using(using_alias).filter(
                parent_id=node.pk, active=True, status=True
            ).order_by('code')
        )
        if not children:
            return node
        stack.extend(reversed(children))
    return None


def resolve_statement_offset_account(using_alias, stmt_line, bank_chart_pk, offset_account_id=None):
    exclude = {bank_chart_pk}
    if offset_account_id:
        try:
            acct = ChartOfAccounts.objects.using(using_alias).get(pk=offset_account_id)
            if acct.pk in exclude:
                return None
            return acct
        except ChartOfAccounts.DoesNotExist:
            return None

    if stmt_line.debit_amount and stmt_line.debit_amount > 0:
        for key in ('Miscellaneous Expenses', 'Rounded Off', 'Exchange', 'Indirect Expenses'):
            acct = _first_leaf_account_under(using_alias, key, exclude)
            if acct:
                return acct
    if stmt_line.credit_amount and stmt_line.credit_amount > 0:
        for key in ('Indirect Income', 'Direct Income', 'Interest', 'Exchange'):
            acct = _first_leaf_account_under(using_alias, key, exclude)
            if acct:
                return acct

    qs = ChartOfAccounts.objects.using(using_alias).filter(
        active=True, status=True
    ).exclude(pk__in=exclude)
    for acct in qs.order_by('code'):
        if not ChartOfAccounts.objects.using(using_alias).filter(parent_id=acct.pk).exists():
            return acct
    return None


def create_posted_journal_for_statement_line(
    reconciliation, stmt_line, user, using_alias, offset_account_id=None
):
    chart_account = reconciliation.bank_account.chart_account or ensure_bank_chart_account(
        reconciliation.bank_account
    )
    if not chart_account:
        raise ValueError(
            'This bank account has no linked chart-of-accounts ledger. Link a bank ledger first.'
        )

    offset = resolve_statement_offset_account(
        using_alias, stmt_line, chart_account.pk, offset_account_id=offset_account_id
    )
    if not offset:
        raise ValueError(
            'No suitable offset account found. Add ledger accounts under Income or Expenses, '
            'or pass offset_account_id when calling this API.'
        )

    entry_number = _next_journal_entry_number(using_alias)
    narration = f'Bank reconciliation: {(stmt_line.description or "")[:200]}'

    je = JournalEntry.objects.using(using_alias).create(
        entry_number=entry_number,
        date=stmt_line.statement_date,
        reference=(stmt_line.reference or '')[:100],
        narration=narration,
        status='posted',
        created_by=user,
        updated_by=user,
    )

    desc = (stmt_line.description or '')[:255]

    if stmt_line.debit_amount and stmt_line.debit_amount > 0:
        amt = stmt_line.debit_amount
        JournalLine.objects.using(using_alias).create(
            journal=je, account=chart_account, description=desc,
            debit=Decimal('0.00'), credit=amt, sequence=10, status=True,
        )
        JournalLine.objects.using(using_alias).create(
            journal=je, account=offset, description=desc,
            debit=amt, credit=Decimal('0.00'), sequence=20, status=True,
        )
    else:
        amt = stmt_line.credit_amount
        JournalLine.objects.using(using_alias).create(
            journal=je, account=chart_account, description=desc,
            debit=amt, credit=Decimal('0.00'), sequence=10, status=True,
        )
        JournalLine.objects.using(using_alias).create(
            journal=je, account=offset, description=desc,
            debit=Decimal('0.00'), credit=amt, sequence=20, status=True,
        )

    lines = list(JournalLine.objects.using(using_alias).filter(journal=je))
    je.total_debit = sum((ln.debit or Decimal('0')) for ln in lines)
    je.total_credit = sum((ln.credit or Decimal('0')) for ln in lines)
    je.save(using=using_alias, update_fields=['total_debit', 'total_credit'])

    TransactionLoader.load_journal_entries(reconciliation, using_alias=using_alias)

    bank_jl = JournalLine.objects.using(using_alias).filter(
        journal=je, account_id=chart_account.pk
    ).first()
    if not bank_jl:
        raise ValueError('Journal was saved but the bank line was not found.')

    recon_line = BankReconciliationLine.objects.using(using_alias).filter(
        reconciliation=reconciliation,
        transaction_type='journal',
        transaction_id=bank_jl.id,
    ).first()
    if not recon_line:
        raise ValueError(
            'Journal line was not loaded into this reconciliation. '
            'Check that the entry date is within the reconciliation period and the bank ledger matches.'
        )

    _persist_statement_match(
        stmt_line,
        recon_line,
        'manually_matched',
        auto_matched=False,
        using_alias=using_alias,
    )

    return recon_line, je


# ─────────────────────────────────────────────────────────────
#  Start Reconciliation Helper
# ─────────────────────────────────────────────────────────────

def start_reconciliation(reconciliation, auto_match=True):
    result = {
        'success': True,
        'transactions_loaded': 0,
        'auto_matched': 0,
        'warnings': [],
        'errors': [],
    }
    try:
        loader = TransactionLoader()
        alias = _get_reconciliation_db_alias(reconciliation)
        loaded = loader.load_journal_entries(reconciliation, using_alias=alias)
        result['transactions_loaded'] = loaded

        if loaded == 0:
            result['warnings'].append(
                'No system transactions (journal entries) were found for this reconciliation period.'
            )

        if auto_match and fetch_statement_lines(reconciliation, using_alias=alias).exists():
            matcher = ReconciliationAutoMatcher(reconciliation, using_alias=alias)
            matched = matcher.auto_match_all()
            result['auto_matched'] = matched

    except Exception as e:
        result['success'] = False
        result['errors'].append(str(e))

    return result
