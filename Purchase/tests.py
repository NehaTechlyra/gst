from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from company.models import Company
from Purchase.models import Bill, PaymentStatus
from Tax.models import TcsMaster, TdsMaster


class BillEditTdsTcsPrefillTests(TestCase):
    def test_bill_edit_context_includes_tds_tcs_values(self):
        company = Company.objects.create(name='Test Company', country='IN', tax_type='GST')
        PaymentStatus.objects.get_or_create(id=1, defaults={'name': 'Not Paid'})
        user = get_user_model().objects.create_superuser(username='billtester', email='billtester@example.com', password='secret123')

        bill = Bill.objects.create(
            bill_number='BN-TEST-001',
            date=date.today(),
            tds_tcs_type='tcs',
            tds_tcs_definition_id=77,
            tds_tcs_rate=2.5,
            tds_tcs_amount=12.5,
        )
        TdsMaster.objects.create(company=company, tax_name='TDS Test', tax_rate=1.0)
        TcsMaster.objects.create(company=company, tax_name='TCS Test', tax_rate=2.0)

        self.client.force_login(user)
        response = self.client.get(reverse('bill_edit', args=[bill.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tds_tcs_type'], 'tcs')
        self.assertEqual(response.context['tds_tcs_definition_id'], 77)
        self.assertEqual(response.context['tds_tcs_rate'], 2.5)
        self.assertEqual(response.context['tds_tcs_amount'], 12.5)
