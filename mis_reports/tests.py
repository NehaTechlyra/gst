from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import RequestFactory, TestCase
from django.urls import resolve

from company.models import Company
from mis_reports.permissions import can_view_dashboard
from Purchase.models import Bill
from sales.models import SalesInvoice, SalesQuotation
from user.models import User as AppUser
from mis_reports.services import (
    build_export_query_string,
    financial_year_bounds,
    parse_date_range_from_request,
    safe_date_filter,
)
from mis_reports.views import dashboard


class MisReportsDashboardTests(TestCase):
    databases = ('default', 'test_company')

    def setUp(self):
        self.factory = RequestFactory()

        if 'test_company' not in connections.databases:
            connections.databases['test_company'] = connections.databases['default'].copy()

        Company.objects.using('default').get_or_create(
            company_code='demo',
            defaults={
                'name': 'Demo Company',
                'db_name': 'test_company',
                'setup_complete': True,
                'db_created': True,
            },
        )

    def test_dashboard_route_resolves(self):
        match = resolve('/demo/mis-reports/')

        self.assertEqual(match.view_name, 'mis_reports_dashboard')
        self.assertEqual(match.kwargs['company_code'], 'demo')
        self.assertEqual(match.func, dashboard)

    def test_dashboard_page_renders_summary_cards(self):
        response = self.client.get('/demo/mis-reports/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MIS Reports')
        self.assertContains(response, 'Total Sales')

    def test_dashboard_renders_summary_cards_with_sales_and_purchases(self):
        SalesInvoice.objects.using('test_company').create(inv_number='INV-1001', date=date(2024, 1, 10), total_amount=Decimal('1000.00'))
        SalesInvoice.objects.using('test_company').create(inv_number='INV-1002', date=date(2024, 2, 10), total_amount=Decimal('250.00'))
        Bill.objects.using('test_company').create(bill_number='BILL-1001', date=date(2024, 1, 12), total_amount=Decimal('400.00'))

        response = self.client.get(
            '/demo/mis-reports/',
            {'period': 'custom', 'start_date': '2024-01-01', 'end_date': '2024-01-31'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['summary']['total_sales'], Decimal('1000.00'))
        self.assertEqual(response.context['summary']['total_purchases'], Decimal('400.00'))
        self.assertEqual(response.context['summary']['gross_profit'], Decimal('600.00'))
        self.assertTrue(any(card['title'] == 'Total Sales' for card in response.context['summary_cards']))

    def test_sales_report_route_resolves(self):
        match = resolve('/demo/mis-reports/sales/')

        self.assertEqual(match.view_name, 'mis_sales_report')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_sales_report_csv_route_resolves(self):
        match = resolve('/demo/mis-reports/sales/export-csv/')

        self.assertEqual(match.view_name, 'mis_sales_report_export_csv')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_purchase_report_route_resolves(self):
        match = resolve('/demo/mis-reports/purchase/')

        self.assertEqual(match.view_name, 'mis_purchase_report')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_purchase_report_csv_route_resolves(self):
        match = resolve('/demo/mis-reports/purchase/export-csv/')

        self.assertEqual(match.view_name, 'mis_purchase_report_export_csv')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_inventory_report_route_resolves(self):
        match = resolve('/demo/mis-reports/inventory/')

        self.assertEqual(match.view_name, 'mis_inventory_report')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_inventory_report_csv_route_resolves(self):
        match = resolve('/demo/mis-reports/inventory/export-csv/')

        self.assertEqual(match.view_name, 'mis_inventory_report_export_csv')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_purchase_report_renders_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_purchase',
            email='misadmin_purchase@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        Bill.objects.using('test_company').create(
            bill_number='BILL-1002',
            date=date(2024, 3, 10),
            total_amount=Decimal('800.00'),
        )

        response = self.client.get('/demo/mis-reports/purchase/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Purchase MIS Report')
        self.assertContains(response, 'Total Purchases')
        self.assertEqual(response.context['report']['purchase_count'], 1)
        self.assertEqual(response.context['report']['total_purchases'], Decimal('800.00'))

    def test_purchase_report_export_csv_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_purchase2',
            email='misadmin_purchase2@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        Bill.objects.using('test_company').create(
            bill_number='BILL-1003',
            date=date(2024, 4, 15),
            total_amount=Decimal('650.00'),
        )

        response = self.client.get('/demo/mis-reports/purchase/export-csv/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('mis_purchase_report.csv', response['Content-Disposition'])
        self.assertIn('Total Purchases,650.00', response.content.decode('utf-8'))

    def test_inventory_report_renders_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_inventory',
            email='misadmin_inventory@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        response = self.client.get('/demo/mis-reports/inventory/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory MIS Report')
        self.assertContains(response, 'Stock Value')

    def test_inventory_report_export_csv_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_inventory2',
            email='misadmin_inventory2@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        response = self.client.get('/demo/mis-reports/inventory/export-csv/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('mis_inventory_report.csv', response['Content-Disposition'])
        self.assertIn('Inventory MIS Report', response.content.decode('utf-8'))

    def test_finance_report_route_resolves(self):
        match = resolve('/demo/mis-reports/finance/')

        self.assertEqual(match.view_name, 'mis_finance_report')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_finance_report_csv_route_resolves(self):
        match = resolve('/demo/mis-reports/finance/export-csv/')

        self.assertEqual(match.view_name, 'mis_finance_report_export_csv')
        self.assertEqual(match.kwargs['company_code'], 'demo')

    def test_finance_report_renders_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_finance',
            email='misadmin_finance@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        response = self.client.get('/demo/mis-reports/finance/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Finance MIS Report')
        self.assertContains(response, 'Total Income')

    def test_finance_report_export_csv_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin_finance2',
            email='misadmin_finance2@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        response = self.client.get('/demo/mis-reports/finance/export-csv/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('mis_finance_report.csv', response['Content-Disposition'])
        self.assertIn('Finance MIS Report', response.content.decode('utf-8'))

    def test_sales_report_renders_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin',
            email='misadmin@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        SalesInvoice.objects.using('test_company').create(inv_number='INV-1003', date=date(2024, 3, 5), total_amount=Decimal('1100.00'))
        SalesQuotation.objects.using('test_company').create(quote_number='QUO-1001', date=date(2024, 3, 6), total_amount=Decimal('500.00'))

        response = self.client.get('/demo/mis-reports/sales/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sales MIS Report')
        self.assertContains(response, 'Total Sales')
        self.assertEqual(response.context['report']['invoice_count'], 1)
        self.assertEqual(response.context['report']['quotation_count'], 1)

    def test_staff_admin_user_can_access_all_mis_reports(self):
        admin = get_user_model().objects.create_user(
            username='staffadmin',
            email='staffadmin@example.com',
            password='testpass123',
            is_staff=False,
        )
        company = Company.objects.using('default').get(company_code='demo')
        AppUser.objects.using('default').create(
            usr_name='staffadmin',
            usr_pwd='testpass123',
            usr_mail='staffadmin@example.com',
            is_admin=True,
            company=company,
        )

        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        for path in [
            '/demo/mis-reports/sales/',
            '/demo/mis-reports/purchase/',
            '/demo/mis-reports/inventory/',
            '/demo/mis-reports/finance/',
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, msg=f'Failed on {path}')

    def test_sales_report_export_csv_for_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username='misadmin2',
            email='misadmin2@example.com',
            password='testpass123',
        )
        self.client.force_login(admin)
        self.client.session['company_id'] = 1
        self.client.session.save()

        SalesInvoice.objects.using('test_company').create(inv_number='INV-1004', date=date(2024, 4, 5), total_amount=Decimal('1200.00'))

        response = self.client.get('/demo/mis-reports/sales/export-csv/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('mis_sales_report.csv', response['Content-Disposition'])
        self.assertIn('Total Sales,1200.00', response.content.decode('utf-8'))

    def test_permission_helpers_respect_superuser_and_regular_users(self):
        user = get_user_model().objects.create_user(username='misuser', password='testpass123')
        self.client.force_login(user)
        self.client.session['company_id'] = 1
        self.client.session.save()

        response = self.client.get('/demo/mis-reports/', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/company/setup/', response.url)


class MisReportsServicesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_parse_date_range_from_request_supports_periods(self):
        request = self.factory.get('/demo/mis-reports/', {'period': 'today'})

        start_date, end_date, period = parse_date_range_from_request(request)

        self.assertEqual(period, 'today')
        self.assertEqual(start_date, date.today())
        self.assertEqual(end_date, date.today())

    def test_parse_date_range_from_request_supports_custom_dates(self):
        request = self.factory.get(
            '/demo/mis-reports/',
            {'period': 'custom', 'start_date': '2024-01-01', 'end_date': '2024-01-31'},
        )

        start_date, end_date, period = parse_date_range_from_request(request)

        self.assertEqual(period, 'custom')
        self.assertEqual(start_date, date(2024, 1, 1))
        self.assertEqual(end_date, date(2024, 1, 31))

    def test_financial_year_bounds_use_april_start(self):
        start_date, end_date = financial_year_bounds(date(2025, 2, 14))

        self.assertEqual(start_date, date(2024, 4, 1))
        self.assertEqual(end_date, date(2025, 3, 31))

    def test_safe_date_filter_applies_bounds_to_queryset(self):
        class FakeQuerySet:
            def __init__(self):
                self.filters = {}

            def filter(self, **kwargs):
                self.filters.update(kwargs)
                return self

        queryset = FakeQuerySet()
        result = safe_date_filter(queryset, 'created_at', '2024-01-01', '2024-01-31')

        self.assertIs(result, queryset)
        self.assertEqual(queryset.filters, {
            'created_at__gte': date(2024, 1, 1),
            'created_at__lte': date(2024, 1, 31),
        })

    def test_build_export_query_string_preserves_filters(self):
        querystring = build_export_query_string({'period': 'this_month', 'start_date': '2024-01-01'})

        self.assertIn('period=this_month', querystring)
        self.assertIn('start_date=2024-01-01', querystring)
        self.assertIn('export=1', querystring)
