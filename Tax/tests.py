from django.test import TestCase

from .forms import TaxForm
from .models import Tax


class TaxFormVisibilityTests(TestCase):
    def test_tax_scope_hidden_on_create_for_non_sales_company(self):
        form = TaxForm(show_optional_fields=False, company_tax_type="GST")
        self.assertNotIn("tax_scope", form.fields)

    def test_tax_scope_visible_on_create_for_sales_company(self):
        form = TaxForm(show_optional_fields=False, company_tax_type="SALES")
        self.assertIn("tax_scope", form.fields)

    def test_tax_scope_hidden_on_edit(self):
        existing = Tax(pk=1)
        form = TaxForm(instance=existing, show_optional_fields=False, company_tax_type="GST")
        self.assertNotIn("tax_scope", form.fields)
