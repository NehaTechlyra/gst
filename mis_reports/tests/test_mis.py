from types import SimpleNamespace
from decimal import Decimal
from datetime import date

from django.test import SimpleTestCase, RequestFactory


class MISReportsTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_permission_check_dashboard(self):
        from mis_reports.permissions import can_view_dashboard

        user = SimpleNamespace(is_superuser=True, is_authenticated=True)
        self.assertTrue(can_view_dashboard(user))

    def test_permission_denial_redirect_for_sales(self):
        request = self.rf.get('/demo/mis-reports/sales/')
        # non-superuser and no special perms
        request.user = SimpleNamespace(is_superuser=False, is_authenticated=True)
        # Provide company_code so redirect_with_company can build URL
        request.resolver_match = SimpleNamespace(kwargs={'company_code': 'demo'})
        # Provide minimal session and messages storage used by views
        request.session = {}
        from django.contrib.messages.storage.fallback import FallbackStorage
        request._messages = FallbackStorage(request)

        from mis_reports import views
        response = views.sales_report(request, company_code='demo')
        self.assertEqual(response.status_code, 302)
        # Redirect should point to the MIS dashboard for the same company
        self.assertIn('/demo/mis-reports/', response.url)

    def test_parse_date_range_today(self):
        request = self.rf.get('/?period=today')
        from mis_reports.services import parse_date_range_from_request

        start, end, period = parse_date_range_from_request(request)
        self.assertEqual(start, date.today())
        self.assertEqual(end, date.today())
        self.assertEqual(period, 'today')

    def test_build_sales_report_defaults(self):
        from mis_reports.views import _build_sales_report

        report = _build_sales_report(None, None)
        self.assertIsInstance(report, dict)
        self.assertEqual(report.get('total_sales'), Decimal('0.00'))
        self.assertEqual(report.get('invoice_count'), 0)
        self.assertEqual(report.get('monthly_trend'), [])

    def test_sales_export_csv_superuser(self):
        request = self.rf.get('/demo/mis-reports/sales/export-csv/')
        request.user = SimpleNamespace(is_superuser=True, is_authenticated=True)
        request.resolver_match = SimpleNamespace(kwargs={'company_code': 'demo'})

        from mis_reports import views
        response = views.sales_report_export_csv(request, company_code='demo')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="mis_sales_report.csv"', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('Sales MIS Report', content)
