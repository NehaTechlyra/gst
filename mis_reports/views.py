import csv
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render

from Lyraerp.utils.redirect_utils import redirect_with_company
from .permissions import (
    can_export,
    can_view_finance,
    can_view_inventory,
    can_view_purchase,
    can_view_sales,
    can_view_crm,
    can_view_hr,
    can_view_expense,
)
from .services import build_export_query_string, financial_year_bounds, parse_date_range_from_request, safe_date_filter


def _to_decimal(value):
    try:
        if value in (None, ''):
            return Decimal('0.00')
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00')


def _format_amount(value):
    return f"₹{_to_decimal(value):,.2f}"


def _format_count(value):
    return f"{int(_to_decimal(value)):,}"


def _customer_display_name(customer):
    if not customer:
        return 'Unknown'
    if getattr(customer, 'customer_type', '') == 'company':
        return getattr(customer, 'company_name', '') or str(customer)
    return f"{getattr(customer, 'first_name', '') or ''} {getattr(customer, 'last_name', '') or ''}".strip() or str(customer)


def _customer_display_name_from_row(row):
    if row.get('customer__company_name'):
        return row['customer__company_name']
    first_name = row.get('customer__first_name') or ''
    last_name = row.get('customer__last_name') or ''
    display_name = f"{first_name} {last_name}".strip()
    if display_name:
        return display_name
    return row.get('customer__customer_code') or 'Unknown'


def _vendor_display_name_from_row(row):
    if row.get('vendor__company_name'):
        return row['vendor__company_name']
    first_name = row.get('vendor__first_name') or ''
    last_name = row.get('vendor__last_name') or ''
    display_name = f"{first_name} {last_name}".strip()
    if display_name:
        return display_name
    return row.get('vendor__vendor_code') or 'Unknown'


def _build_summary(start_date=None, end_date=None):
    summary = {
        'total_sales': Decimal('0.00'),
        'total_purchases': Decimal('0.00'),
        'gross_profit': Decimal('0.00'),
        'outstanding_receivables': Decimal('0.00'),
        'outstanding_payables': Decimal('0.00'),
        'stock_value': Decimal('0.00'),
        'low_stock_count': 0,
        'lead_opportunity_count': 0,
        'employee_count': 0,
        'monthly_expenses': Decimal('0.00'),
    }

    try:
        from sales.models import SalesInvoice

        sales_queryset = safe_date_filter(SalesInvoice.objects.all(), 'date', start_date, end_date)
        summary['total_sales'] = sales_queryset.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
    except Exception:
        summary['total_sales'] = Decimal('0.00')

    try:
        from Purchase.models import Bill

        purchase_queryset = safe_date_filter(Bill.objects.all(), 'date', start_date, end_date)
        summary['total_purchases'] = purchase_queryset.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
    except Exception:
        summary['total_purchases'] = Decimal('0.00')

    summary['gross_profit'] = summary['total_sales'] - summary['total_purchases']

    try:
        from sales.models import SalesInvoice, InvPaymentAllocation

        invoices = safe_date_filter(SalesInvoice.objects.all(), 'date', start_date, end_date)
        invoice_total = invoices.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total'] or Decimal('0.00')
        allocations = InvPaymentAllocation.objects.filter(inv__in=invoices)
        if start_date and end_date:
            allocations = allocations.filter(payment__payment_date__gte=start_date, payment__payment_date__lte=end_date)
        received_total = allocations.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total'] or Decimal('0.00')
        summary['outstanding_receivables'] = max(invoice_total - received_total, Decimal('0.00'))
    except Exception:
        summary['outstanding_receivables'] = Decimal('0.00')

    try:
        from Purchase.models import Bill, BillPaymentAllocation

        bills = safe_date_filter(Bill.objects.all(), 'date', start_date, end_date)
        bill_total = bills.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total'] or Decimal('0.00')
        allocations = BillPaymentAllocation.objects.filter(bill__in=bills)
        if start_date and end_date:
            allocations = allocations.filter(payment__payment_date__gte=start_date, payment__payment_date__lte=end_date)
        paid_total = allocations.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total'] or Decimal('0.00')
        summary['outstanding_payables'] = max(bill_total - paid_total, Decimal('0.00'))
    except Exception:
        summary['outstanding_payables'] = Decimal('0.00')

    try:
        from stock.models import Stock

        stock_items = Stock.objects.select_related('item').all()
        stock_value = Decimal('0.00')
        low_stock_count = 0
        for stock in stock_items:
            quantity = _to_decimal(getattr(stock, 'quantity', 0))
            rate = _to_decimal(getattr(getattr(stock, 'item', None), 'cost_price', 0))
            stock_value += quantity * rate
            min_stock = getattr(getattr(stock, 'item', None), 'min_stock', None)
            if min_stock is not None and quantity <= _to_decimal(min_stock):
                low_stock_count += 1
        summary['stock_value'] = stock_value
        summary['low_stock_count'] = low_stock_count
    except Exception:
        summary['stock_value'] = Decimal('0.00')
        summary['low_stock_count'] = 0

    try:
        from crm.models import Lead, Opportunity

        lead_count = safe_date_filter(Lead.objects.all(), 'created_at', start_date, end_date).count()
        opportunity_count = safe_date_filter(Opportunity.objects.all(), 'created_at', start_date, end_date).count()
        summary['lead_opportunity_count'] = lead_count + opportunity_count
    except Exception:
        summary['lead_opportunity_count'] = 0

    try:
        from Employee.models import Employee

        summary['employee_count'] = Employee.objects.count()
    except Exception:
        summary['employee_count'] = 0

    try:
        from expenses.models import Expense

        expense_queryset = safe_date_filter(Expense.objects.all(), 'date', start_date, end_date)
        expense_total = Decimal('0.00')
        for expense in expense_queryset:
            expense_total += _to_decimal(getattr(expense, 'total_amount', 0))
        summary['monthly_expenses'] = expense_total
    except Exception:
        summary['monthly_expenses'] = Decimal('0.00')

    return summary


def dashboard(request, company_code=None):
    start_date, end_date, period = parse_date_range_from_request(request)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    summary = _build_summary(start_date, end_date)
    summary_cards = [
        {'title': 'Total Sales', 'value': _format_amount(summary['total_sales']), 'description': 'Sales invoices in the selected period.'},
        {'title': 'Total Purchases', 'value': _format_amount(summary['total_purchases']), 'description': 'Purchase bills in the selected period.'},
        {'title': 'Gross Profit', 'value': _format_amount(summary['gross_profit']), 'description': 'Estimated sales minus purchases.'},
        {'title': 'Outstanding Receivables', 'value': _format_amount(summary['outstanding_receivables']), 'description': 'Open customer receivables for matching invoices.'},
        {'title': 'Outstanding Payables', 'value': _format_amount(summary['outstanding_payables']), 'description': 'Open vendor payables for matching bills.'},
        {'title': 'Stock Value', 'value': _format_amount(summary['stock_value']), 'description': 'Current inventory value based on stock records.'},
        {'title': 'Low Stock Items', 'value': _format_count(summary['low_stock_count']), 'description': 'Items at or below minimum stock levels.'},
        {'title': 'Leads & Opportunities', 'value': _format_count(summary['lead_opportunity_count']), 'description': 'New leads and opportunities in the period.'},
        {'title': 'Employees', 'value': _format_count(summary['employee_count']), 'description': 'Registered employees in the system.'},
        {'title': 'Monthly Expenses', 'value': _format_amount(summary['monthly_expenses']), 'description': 'Expenses recorded in the selected period.'},
    ]

    return render(request, 'mis_reports/dashboard.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'export_query_string': export_query_string,
        'summary': summary,
        'summary_cards': summary_cards,
    })


def _build_sales_report(start_date=None, end_date=None):
    report = {
        'total_sales': Decimal('0.00'),
        'invoice_count': 0,
        'quotation_count': 0,
        'top_customers': [],
        'top_items': [],
        'monthly_trend': [],
        'outstanding_sales': Decimal('0.00'),
    }

    try:
        from sales.models import InvPaymentAllocation, SalesInvoice, SalesInvoiceItem, SalesQuotation

        invoices = safe_date_filter(SalesInvoice.objects.all(), 'date', start_date, end_date)
        report['invoice_count'] = invoices.count()
        report['total_sales'] = invoices.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')

        report['quotation_count'] = safe_date_filter(
            SalesQuotation.objects.all(), 'date', start_date, end_date
        ).count()

        customer_rows = invoices.filter(customer__isnull=False).values(
            'customer',
            'customer__company_name',
            'customer__first_name',
            'customer__last_name',
            'customer__customer_code',
        ).annotate(
            total_sales=Coalesce(Sum('total_amount'), Decimal('0.00')),
            invoice_count=Count('pk'),
        ).order_by('-total_sales')[:10]

        for row in customer_rows:
            report['top_customers'].append({
                'customer_name': _customer_display_name_from_row(row),
                'total_sales': row['total_sales'] or Decimal('0.00'),
                'invoice_count': row['invoice_count'],
            })

        item_rows = SalesInvoiceItem.objects.filter(sales_inv__in=invoices).values(
            'product__name',
        ).annotate(
            quantity_sold=Coalesce(Sum('quantity'), Decimal('0.00')),
        ).order_by('-quantity_sold')[:10]

        for row in item_rows:
            report['top_items'].append({
                'item_name': row.get('product__name') or 'Unknown',
                'quantity_sold': row['quantity_sold'] or Decimal('0.00'),
            })

        trend_rows = invoices.annotate(month=TruncMonth('date')).values('month').annotate(
            total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'))
        ).order_by('month')

        for row in trend_rows:
            month = row.get('month')
            report['monthly_trend'].append({
                'month': month.strftime('%Y-%m') if month else 'Unknown',
                'total_sales': row['total_sales'] or Decimal('0.00'),
            })

        paid_amount = InvPaymentAllocation.objects.filter(inv__in=invoices).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
        report['outstanding_sales'] = max(report['total_sales'] - paid_amount, Decimal('0.00'))
    except Exception:
        pass

    return report


def _build_purchase_report(start_date=None, end_date=None):
    report = {
        'total_purchases': Decimal('0.00'),
        'purchase_count': 0,
        'top_vendors': [],
        'top_items': [],
        'monthly_trend': [],
        'outstanding_purchases': Decimal('0.00'),
    }

    try:
        from Purchase.models import Bill, BillItem, BillPaymentAllocation

        bills = safe_date_filter(Bill.objects.all(), 'date', start_date, end_date)
        report['purchase_count'] = bills.count()
        report['total_purchases'] = bills.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')

        vendor_rows = bills.filter(vendor__isnull=False).values(
            'vendor',
            'vendor__company_name',
            'vendor__first_name',
            'vendor__last_name',
            'vendor__vendor_code',
        ).annotate(
            total_purchases=Coalesce(Sum('total_amount'), Decimal('0.00')),
            bill_count=Count('pk'),
        ).order_by('-total_purchases')[:10]

        for row in vendor_rows:
            report['top_vendors'].append({
                'vendor_name': _vendor_display_name_from_row(row),
                'total_purchases': row['total_purchases'] or Decimal('0.00'),
                'bill_count': row['bill_count'],
            })

        item_rows = BillItem.objects.filter(bill__in=bills).values(
            'product__name',
        ).annotate(
            quantity_purchased=Coalesce(Sum('quantity'), Decimal('0.00')),
        ).order_by('-quantity_purchased')[:10]

        for row in item_rows:
            report['top_items'].append({
                'item_name': row.get('product__name') or 'Unknown',
                'quantity_purchased': row['quantity_purchased'] or Decimal('0.00'),
            })

        trend_rows = bills.annotate(month=TruncMonth('date')).values('month').annotate(
            total_purchases=Coalesce(Sum('total_amount'), Decimal('0.00'))
        ).order_by('month')

        for row in trend_rows:
            month = row.get('month')
            report['monthly_trend'].append({
                'month': month.strftime('%Y-%m') if month else 'Unknown',
                'total_purchases': row['total_purchases'] or Decimal('0.00'),
            })

        paid_amount = BillPaymentAllocation.objects.filter(bill__in=bills).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
        report['outstanding_purchases'] = max(report['total_purchases'] - paid_amount, Decimal('0.00'))
    except Exception:
        pass

    return report


def _build_inventory_report(start_date=None, end_date=None):
    report = {
        'stock_value': Decimal('0.00'),
        'low_stock_items': [],
        'out_of_stock_items': [],
        'fast_moving_items': [],
        'slow_moving_items': [],
        'warehouse_summary': [],
        'category_summary': [],
    }

    try:
        from stock.models import Stock
        from sales.models import SalesInvoiceItem

        stocks = Stock.objects.filter(status=True, item__status=True).select_related('item', 'warehouse')
        if not stocks.exists():
            return report

        product_stats = {}
        warehouse_stats = {}
        category_stats = {}

        for stock in stocks:
            quantity = _to_decimal(stock.quantity)
            item = stock.item
            cost_price = _to_decimal(item.cost_price or getattr(item, 'op_rate', 0))
            stock_value = quantity * cost_price
            report['stock_value'] += stock_value

            product_id = item.id
            category_name = item.category.name if item.category_id else 'Uncategorized'
            warehouse_name = stock.warehouse.warehouse_name if stock.warehouse_id else 'Unknown'

            if product_id not in product_stats:
                product_stats[product_id] = {
                    'item_name': item.name,
                    'total_quantity': Decimal('0.00'),
                    'stock_value': Decimal('0.00'),
                    'min_stock': _to_decimal(item.min_stock or 0),
                    'quantity_sold': Decimal('0.00'),
                    'category': category_name,
                }

            product_stats[product_id]['total_quantity'] += quantity
            product_stats[product_id]['stock_value'] += stock_value

            warehouse_stats.setdefault(warehouse_name, {
                'warehouse_name': warehouse_name,
                'total_quantity': Decimal('0.00'),
                'stock_value': Decimal('0.00'),
            })
            warehouse_stats[warehouse_name]['total_quantity'] += quantity
            warehouse_stats[warehouse_name]['stock_value'] += stock_value

            category_stats.setdefault(category_name, {
                'category_name': category_name,
                'total_quantity': Decimal('0.00'),
                'stock_value': Decimal('0.00'),
            })
            category_stats[category_name]['total_quantity'] += quantity
            category_stats[category_name]['stock_value'] += stock_value

        sales_qs = SalesInvoiceItem.objects.filter(product__status=True)
        if start_date:
            sales_qs = sales_qs.filter(sales_inv__date__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(sales_inv__date__lte=end_date)

        for row in sales_qs.values('product_id').annotate(quantity_sold=Sum('quantity')):
            product_id = row['product_id']
            if product_id in product_stats:
                product_stats[product_id]['quantity_sold'] = _to_decimal(row['quantity_sold'] or 0)

        report['fast_moving_items'] = sorted(
            product_stats.values(),
            key=lambda x: x['quantity_sold'],
            reverse=True,
        )[:10]

        report['slow_moving_items'] = sorted(
            [item for item in product_stats.values() if item['total_quantity'] > 0],
            key=lambda x: x['quantity_sold'],
        )[:10]

        report['low_stock_items'] = [
            item for item in product_stats.values()
            if item['min_stock'] > 0 and item['total_quantity'] <= item['min_stock'] and item['total_quantity'] > 0
        ][:10]

        report['out_of_stock_items'] = [
            item for item in product_stats.values()
            if item['total_quantity'] <= 0
        ][:10]

        report['warehouse_summary'] = sorted(warehouse_stats.values(), key=lambda x: x['warehouse_name'])
        report['category_summary'] = sorted(category_stats.values(), key=lambda x: x['category_name'])
    except Exception:
        pass

    return report


def _build_finance_report(start_date=None, end_date=None):
    report = {
        'total_income': Decimal('0.00'),
        'total_expenses': Decimal('0.00'),
        'net_profit_loss': Decimal('0.00'),
        'opening_stock': Decimal('0.00'),
        'closing_stock': Decimal('0.00'),
        'stock_adjustments': Decimal('0.00'),
        'cash_summary': {
            'opening_cash': Decimal('0.00'),
            'closing_cash': Decimal('0.00'),
            'net_change': Decimal('0.00'),
        },
        'receivables_balance': Decimal('0.00'),
        'payables_balance': Decimal('0.00'),
        'income_groups': [],
        'expense_groups': [],
        'monthly_profit_trend': [],
    }

    try:
        from chart_of_accounts.balance_sheet import (
            generate_profit_loss,
            generate_cash_flow_statement,
            get_account_balance,
        )
        from chart_of_accounts.models import ChartOfAccounts
        from datetime import date, timedelta
        from sales.models import SalesInvoice
        from Purchase.models import Bill

        fy_start_date, _ = financial_year_bounds(end_date or date.today())
        pl_data = generate_profit_loss(start_date, end_date, fy_start_date)
        cash_data = generate_cash_flow_statement(start_date, end_date, fy_start_date=fy_start_date)

        report['total_income'] = Decimal(str(pl_data.get('sales', 0))) + Decimal(str(pl_data.get('non_operating_income', 0)))
        report['total_expenses'] = Decimal(str(pl_data.get('cogs', 0))) + Decimal(str(pl_data.get('operating_expenses_total', 0)))
        report['net_profit_loss'] = Decimal(str(pl_data.get('net_profit_loss', 0)))
        report['opening_stock'] = Decimal(str(pl_data.get('opening_stock', 0)))
        report['closing_stock'] = Decimal(str(pl_data.get('closing_stock', 0)))
        report['stock_adjustments'] = Decimal(str(pl_data.get('stock_adjustments', 0)))

        report['cash_summary'] = {
            'opening_cash': Decimal(str(cash_data.get('cash_movement', {}).get('opening_cash_balance', 0))),
            'closing_cash': Decimal(str(cash_data.get('cash_movement', {}).get('closing_cash_balance', 0))),
            'net_change': Decimal(str(cash_data.get('cash_movement', {}).get('net_change_in_cash', 0))),
        }

        report['income_groups'] = pl_data.get('income', [])
        report['expense_groups'] = pl_data.get('expenses', [])

        receivables_balance = Decimal('0.00')
        payables_balance = Decimal('0.00')
        for account in ChartOfAccounts.objects.filter(status=True):
            name = (account.name or '').lower()
            balance = Decimal(str(get_account_balance(account, as_of_date=end_date)))
            if 'receivable' in name or 'debtor' in name or 'accounts receivable' in name:
                receivables_balance += balance
            if 'payable' in name or 'creditor' in name or 'accounts payable' in name or 'supplier' in name:
                payables_balance += balance

        report['receivables_balance'] = receivables_balance
        report['payables_balance'] = payables_balance

        if start_date and end_date:
            current = start_date.replace(day=1)
            until = end_date.replace(day=1)
            while current <= until:
                next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
                month_end = next_month - timedelta(days=1)
                sales = SalesInvoice.objects.filter(date__gte=current, date__lte=month_end).aggregate(
                    total=Coalesce(Sum('total_amount'), Decimal('0.00'))
                )['total'] or Decimal('0.00')
                purchases = Bill.objects.filter(date__gte=current, date__lte=month_end).aggregate(
                    total=Coalesce(Sum('total_amount'), Decimal('0.00'))
                )['total'] or Decimal('0.00')
                report['monthly_profit_trend'].append({
                    'month': current.strftime('%Y-%m'),
                    'sales': sales,
                    'purchases': purchases,
                    'profit': sales - purchases,
                })
                current = next_month
    except Exception:
        pass

    return report


def _build_crm_report(start_date=None, end_date=None):
    report = {
        'lead_count': 0,
        'opportunity_count': 0,
        'won_deals': 0,
        'lost_deals': 0,
        'conversion_rate': 0.0,
        'followups': {
            'pending': 0,
            'completed': 0,
        },
        'pipeline_value': Decimal('0.00'),
        'source_wise': [],
    }

    try:
        from crm.models import Lead, Opportunity, FollowUp
        from django.db.models import Count

        leads = safe_date_filter(Lead.objects.all(), 'created_at', start_date, end_date)
        opps = safe_date_filter(Opportunity.objects.all(), 'created_at', start_date, end_date)

        report['lead_count'] = leads.count()
        report['opportunity_count'] = opps.count()

        report['won_deals'] = opps.filter(status__iexact='Closed Won').count()
        report['lost_deals'] = opps.filter(status__iexact='Closed Lost').count()

        if report['lead_count']:
            report['conversion_rate'] = float(report['won_deals']) / float(report['lead_count']) * 100.0
        else:
            report['conversion_rate'] = 0.0

        followups = FollowUp.objects.all()
        if start_date:
            followups = followups.filter(followup_date__gte=start_date)
        if end_date:
            followups = followups.filter(followup_date__lte=end_date)

        report['followups']['pending'] = followups.filter(status__iexact='Pending').count()
        report['followups']['completed'] = followups.filter(status__iexact='Completed').count()

        # Pipeline value: sum of estimated_deal_value for open opportunities
        open_statuses = ['Open', 'Discussion', 'Quotation Created']
        pipeline_qs = Opportunity.objects.filter(status__in=open_statuses)
        if start_date:
            pipeline_qs = pipeline_qs.filter(created_at__gte=start_date)
        if end_date:
            pipeline_qs = pipeline_qs.filter(created_at__lte=end_date)
        pipeline_sum = pipeline_qs.aggregate(total=Coalesce(Sum('estimated_deal_value'), Decimal('0.00')))['total'] or Decimal('0.00')
        report['pipeline_value'] = pipeline_sum

        # Source-wise leads
        source_rows = leads.values('source').annotate(count=Count('pk')).order_by('-count')
        for row in source_rows:
            report['source_wise'].append({'source': row.get('source') or 'Unknown', 'count': row.get('count', 0)})
    except Exception:
        pass

    return report


def sales_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_sales(request.user)):
        messages.error(request, 'You do not have permission to view Sales MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_sales_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/sales_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def sales_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_sales_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_sales_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Sales MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Total Sales', f'{report_data["total_sales"]:.2f}'])
    writer.writerow(['Invoice Count', report_data['invoice_count']])
    writer.writerow(['Quotation Count', report_data['quotation_count']])
    writer.writerow(['Outstanding Sales', f'{report_data["outstanding_sales"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Top Customers'])
    writer.writerow(['Customer', 'Invoice Count', 'Total Sales'])
    for customer in report_data['top_customers']:
        writer.writerow([
            customer['customer_name'],
            customer['invoice_count'],
            f'{customer["total_sales"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Top Selling Items'])
    writer.writerow(['Item', 'Quantity Sold'])
    for item in report_data['top_items']:
        writer.writerow([item['item_name'], f'{item["quantity_sold"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Monthly Sales Trend'])
    writer.writerow(['Month', 'Total Sales'])
    for trend in report_data['monthly_trend']:
        writer.writerow([trend['month'], f'{trend["total_sales"]:.2f}'])

    return response


def purchase_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_purchase(request.user)):
        messages.error(request, 'You do not have permission to view Purchase MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_purchase_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/purchase_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def purchase_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_purchase_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_purchase_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Purchase MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Total Purchases', f'{report_data["total_purchases"]:.2f}'])
    writer.writerow(['Purchase Count', report_data['purchase_count']])
    writer.writerow(['Outstanding Purchases', f'{report_data["outstanding_purchases"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Top Vendors'])
    writer.writerow(['Vendor', 'Bill Count', 'Total Purchases'])
    for vendor in report_data['top_vendors']:
        writer.writerow([
            vendor['vendor_name'],
            vendor['bill_count'],
            f'{vendor["total_purchases"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Top Purchased Items'])
    writer.writerow(['Item', 'Quantity Purchased'])
    for item in report_data['top_items']:
        writer.writerow([item['item_name'], f'{item["quantity_purchased"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Monthly Purchase Trend'])
    writer.writerow(['Month', 'Total Purchases'])
    for trend in report_data['monthly_trend']:
        writer.writerow([trend['month'], f'{trend["total_purchases"]:.2f}'])

    return response


def inventory_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_inventory(request.user)):
        messages.error(request, 'You do not have permission to view Inventory MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_inventory_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/inventory_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def inventory_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_inventory_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_inventory_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Inventory MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Stock Value', f'{report_data["stock_value"]:.2f}'])
    writer.writerow(['Low Stock Items', len(report_data['low_stock_items'])])
    writer.writerow(['Out of Stock Items', len(report_data['out_of_stock_items'])])
    writer.writerow([])

    writer.writerow(['Low Stock Items'])
    writer.writerow(['Item', 'Quantity', 'Stock Value'])
    for item in report_data['low_stock_items']:
        writer.writerow([
            item['item_name'],
            f'{item["total_quantity"]:.2f}',
            f'{item["stock_value"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Out of Stock Items'])
    writer.writerow(['Item', 'Stock Value'])
    for item in report_data['out_of_stock_items']:
        writer.writerow([
            item['item_name'],
            f'{item["stock_value"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Fast Moving Items'])
    writer.writerow(['Item', 'Quantity Sold', 'Stock Quantity'])
    for item in report_data['fast_moving_items']:
        writer.writerow([
            item['item_name'],
            f'{item["quantity_sold"]:.2f}',
            f'{item["total_quantity"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Slow Moving Items'])
    writer.writerow(['Item', 'Quantity Sold', 'Stock Quantity'])
    for item in report_data['slow_moving_items']:
        writer.writerow([
            item['item_name'],
            f'{item["quantity_sold"]:.2f}',
            f'{item["total_quantity"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Warehouse Summary'])
    writer.writerow(['Warehouse', 'Total Quantity', 'Stock Value'])
    for warehouse in report_data['warehouse_summary']:
        writer.writerow([
            warehouse['warehouse_name'],
            f'{warehouse["total_quantity"]:.2f}',
            f'{warehouse["stock_value"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Category Summary'])
    writer.writerow(['Category', 'Total Quantity', 'Stock Value'])
    for category in report_data['category_summary']:
        writer.writerow([
            category['category_name'],
            f'{category["total_quantity"]:.2f}',
            f'{category["stock_value"]:.2f}',
        ])

    return response


def finance_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_finance(request.user)):
        messages.error(request, 'You do not have permission to view Finance MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_finance_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/finance_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def finance_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_finance_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_finance_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Finance MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Total Income', f'{report_data["total_income"]:.2f}'])
    writer.writerow(['Total Expenses', f'{report_data["total_expenses"]:.2f}'])
    writer.writerow(['Net Profit/Loss', f'{report_data["net_profit_loss"]:.2f}'])
    writer.writerow(['Opening Stock', f'{report_data["opening_stock"]:.2f}'])
    writer.writerow(['Closing Stock', f'{report_data["closing_stock"]:.2f}'])
    writer.writerow(['Stock Adjustments', f'{report_data["stock_adjustments"]:.2f}'])
    writer.writerow(['Opening Cash', f'{report_data["cash_summary"]["opening_cash"]:.2f}'])
    writer.writerow(['Closing Cash', f'{report_data["cash_summary"]["closing_cash"]:.2f}'])
    writer.writerow(['Receivables Balance', f'{report_data["receivables_balance"]:.2f}'])
    writer.writerow(['Payables Balance', f'{report_data["payables_balance"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Monthly Profit Trend'])
    writer.writerow(['Month', 'Sales', 'Purchases', 'Profit'])
    for row in report_data['monthly_profit_trend']:
        writer.writerow([
            row['month'],
            f'{row["sales"]:.2f}',
            f'{row["purchases"]:.2f}',
            f'{row["profit"]:.2f}',
        ])
    writer.writerow([])

    writer.writerow(['Income Group Summary'])
    writer.writerow(['Name', 'Balance'])
    for group in report_data['income_groups']:
        writer.writerow([group['name'], f'{group["balance"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Expense Group Summary'])
    writer.writerow(['Name', 'Balance'])
    for group in report_data['expense_groups']:
        writer.writerow([group['name'], f'{group["balance"]:.2f}'])

    return response


def crm_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_crm(request.user)):
        messages.error(request, 'You do not have permission to view CRM MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_crm_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/crm_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def crm_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_crm_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_crm_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['CRM MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Lead Count', report_data['lead_count']])
    writer.writerow(['Opportunity Count', report_data['opportunity_count']])
    writer.writerow(['Won Deals', report_data['won_deals']])
    writer.writerow(['Lost Deals', report_data['lost_deals']])
    writer.writerow(['Conversion Rate', f"{report_data['conversion_rate']:.2f}%"])
    writer.writerow(['Pipeline Value', f"{report_data['pipeline_value']:.2f}"])
    writer.writerow([])

    writer.writerow(['Follow-ups'])
    writer.writerow(['Pending', report_data['followups']['pending']])
    writer.writerow(['Completed', report_data['followups']['completed']])
    writer.writerow([])

    writer.writerow(['Source-wise Leads'])
    writer.writerow(['Source', 'Count'])
    for s in report_data['source_wise']:
        writer.writerow([s['source'], s['count']])

    return response


def _build_expense_report(start_date=None, end_date=None):
    report = {
        'total_expenses': Decimal('0.00'),
        'category_wise': [],
        'monthly_trend': [],
        'highest_expenses': [],
        'approved_count': 0,
        'pending_count': 0,
    }

    try:
        from expenses.models import Expense, ExpenseLine

        qs = safe_date_filter(Expense.objects.all(), 'date', start_date, end_date)
        report['total_expenses'] = qs.aggregate(total=Coalesce(Sum('total_amount_base'), Decimal('0.00')))['total'] or Decimal('0.00')

        # Category-wise using ExpenseLine.account.name
        line_qs = ExpenseLine.objects.filter(expense__in=qs)
        cat_rows = line_qs.values('account__name').annotate(total=Coalesce(Sum('amount'), Decimal('0.00'))).order_by('-total')[:10]
        for row in cat_rows:
            report['category_wise'].append({
                'category': row.get('account__name') or 'Unspecified',
                'total': row.get('total') or Decimal('0.00'),
            })

        # Monthly trend
        trend_rows = qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Coalesce(Sum('total_amount_base'), Decimal('0.00'))).order_by('month')
        for row in trend_rows:
            month = row.get('month')
            report['monthly_trend'].append({
                'month': month.strftime('%Y-%m') if month else 'Unknown',
                'total': row.get('total') or Decimal('0.00'),
            })

        # Highest expense entries
        top_expenses = qs.order_by('-total_amount_base')[:10]
        for e in top_expenses:
            report['highest_expenses'].append({
                'id': getattr(e, 'id', None),
                'date': getattr(e, 'date', None),
                'vendor': getattr(e, 'vendor', None) and str(e.vendor) or 'Unknown',
                'amount': getattr(e, 'total_amount_base', Decimal('0.00')),
            })

        # Approved / pending counts if approval field exists
        try:
            if hasattr(Expense, 'approval_status'):
                report['approved_count'] = qs.filter(approval_status__iexact='APPROVED').count()
                report['pending_count'] = qs.filter(approval_status__iexact='PENDING').count()
            elif hasattr(Expense, 'status'):
                # status boolean: treat True as approved-ish
                report['approved_count'] = qs.filter(status=True).count()
                report['pending_count'] = qs.filter(status=False).count()
        except Exception:
            report['approved_count'] = 0
            report['pending_count'] = 0

    except Exception:
        pass

    return report


def expense_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_expense(request.user)):
        messages.error(request, 'You do not have permission to view Expense MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_expense_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/expense_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def expense_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_expense_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_expense_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Expense MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Total Expenses', f'{report_data["total_expenses"]:.2f}'])
    writer.writerow([])

    writer.writerow(['Category-wise Expenses'])
    writer.writerow(['Category', 'Total'])
    for c in report_data['category_wise']:
        writer.writerow([c['category'], f'{c['total']:.2f}'])
    writer.writerow([])

    writer.writerow(['Monthly Trend'])
    writer.writerow(['Month', 'Total'])
    for m in report_data['monthly_trend']:
        writer.writerow([m['month'], f'{m['total']:.2f}'])
    writer.writerow([])

    writer.writerow(['Top Expenses'])
    writer.writerow(['ID', 'Date', 'Vendor', 'Amount'])
    for e in report_data['highest_expenses']:
        writer.writerow([e['id'], e['date'], e['vendor'], f"{_to_decimal(e['amount']):.2f}"])
    writer.writerow([])

    writer.writerow(['Approved Count', report_data['approved_count']])
    writer.writerow(['Pending Count', report_data['pending_count']])

    return response


def _build_hr_report(start_date=None, end_date=None):
    report = {
        'total_employees': 0,
        'active_employees': 0,
        'inactive_employees': 0,
        'department_counts': [],
        'designation_counts': [],
        'leave_type_count': 0,
        'employees_with_leaves': 0,
    }

    try:
        from HR.models import Employee
        # department and designation models
        # Department: department.department_name
        # Designations: designation.designation_name

        qs = Employee.objects.all()
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)

        report['total_employees'] = qs.count()
        report['active_employees'] = qs.filter(status=True).count()
        report['inactive_employees'] = qs.filter(status=False).count()

        # Department-wise counts
        dept_rows = qs.values('department__department_name').annotate(count=Count('pk')).order_by('-count')
        for row in dept_rows:
            report['department_counts'].append({
                'department': row.get('department__department_name') or 'Unknown',
                'count': row.get('count', 0),
            })

        # Designation-wise counts
        desig_rows = qs.values('designation__designation_name').annotate(count=Count('pk')).order_by('-count')
        for row in desig_rows:
            report['designation_counts'].append({
                'designation': row.get('designation__designation_name') or 'Unknown',
                'count': row.get('count', 0),
            })

        # Leaves: count leave types and employees linked to any leave (many-to-many)
        try:
            from leaves.models import Leaves
            report['leave_type_count'] = Leaves.objects.count()
            report['employees_with_leaves'] = qs.filter(leaves__isnull=False).distinct().count()
        except Exception:
            report['leave_type_count'] = 0
            report['employees_with_leaves'] = 0

    except Exception:
        pass

    return report


def hr_report(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_view_hr(request.user)):
        messages.error(request, 'You do not have permission to view HR MIS report.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_hr_report(start_date, end_date)
    export_query_string = build_export_query_string({
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    })

    return render(request, 'mis_reports/hr_report.html', {
        'company_code': company_code,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'report': report_data,
        'can_export': getattr(request.user, 'is_superuser', False) or can_export(request.user),
        'export_query_string': export_query_string,
    })


def hr_report_export_csv(request, company_code=None):
    if not (getattr(request.user, 'is_superuser', False) or can_export(request.user)):
        messages.error(request, 'You do not have permission to export MIS reports.')
        return redirect_with_company(request, 'mis_reports_dashboard')

    start_date, end_date, period = parse_date_range_from_request(request)
    report_data = _build_hr_report(start_date, end_date)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mis_hr_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['HR MIS Report'])
    writer.writerow(['Period', period])
    writer.writerow(['Total Employees', report_data['total_employees']])
    writer.writerow(['Active Employees', report_data['active_employees']])
    writer.writerow(['Inactive Employees', report_data['inactive_employees']])
    writer.writerow([])

    writer.writerow(['Department', 'Count'])
    for d in report_data['department_counts']:
        writer.writerow([d['department'], d['count']])
    writer.writerow([])

    writer.writerow(['Designation', 'Count'])
    for d in report_data['designation_counts']:
        writer.writerow([d['designation'], d['count']])
    writer.writerow([])

    writer.writerow(['Leave Types', report_data['leave_type_count']])
    writer.writerow(['Employees With Leave Types', report_data['employees_with_leaves']])

    return response
