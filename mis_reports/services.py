"""Shared service helpers for MIS report filters and date handling."""

from datetime import date, datetime, timedelta
from urllib.parse import urlencode


VALID_PERIODS = {
    'today',
    'this_week',
    'this_month',
    'this_quarter',
    'this_financial_year',
    'custom',
}


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def financial_year_bounds(for_date=None):
    """Return the start and end dates for the financial year containing the given date."""
    reference = _parse_date(for_date) or date.today()
    if reference.month >= 4:
        start = date(reference.year, 4, 1)
        end = date(reference.year + 1, 3, 31)
    else:
        start = date(reference.year - 1, 4, 1)
        end = date(reference.year, 3, 31)
    return start, end


def parse_date_range_from_request(request, default_period='this_month'):
    """Parse a date range from request query parameters."""
    params = getattr(request, 'GET', None) or {}
    period = (params.get('period') or default_period).strip().lower()

    if period not in VALID_PERIODS:
        period = default_period

    if period == 'custom':
        start_date = _parse_date(params.get('start_date'))
        end_date = _parse_date(params.get('end_date'))
        if start_date and end_date and start_date <= end_date:
            return start_date, end_date, period
        return date.today(), date.today(), period

    today = date.today()
    if period == 'today':
        return today, today, period

    if period == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        return start_date, today, period

    if period == 'this_month':
        start_date = date(today.year, today.month, 1)
        return start_date, today, period

    if period == 'this_quarter':
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, quarter_start_month, 1)
        return start_date, today, period

    if period == 'this_financial_year':
        start_date, end_date = financial_year_bounds(today)
        return start_date, end_date, period

    return today, today, period


def safe_date_filter(queryset, field_name, start_date=None, end_date=None):
    """Apply safe start/end bounds to a queryset for date filtering."""
    parsed_start = _parse_date(start_date)
    parsed_end = _parse_date(end_date)

    if parsed_start and parsed_end and parsed_start <= parsed_end:
        return queryset.filter(**{f'{field_name}__gte': parsed_start, f'{field_name}__lte': parsed_end})

    if parsed_start:
        return queryset.filter(**{f'{field_name}__gte': parsed_start})

    if parsed_end:
        return queryset.filter(**{f'{field_name}__lte': parsed_end})

    return queryset


def build_export_query_string(filters=None, include_export=True):
    """Build a query string that preserves filter state for export links."""
    params = dict(filters or {})
    if include_export:
        params['export'] = '1'

    return urlencode(sorted(params.items()))

