from django.test import TestCase
from unittest.mock import MagicMock, patch

from Tax.models import Tax

from .models import Item
from .views import _assign_item_tax_fields, _validate_item_tax_selection
from Lyraerp.utils.thread_locals import clear_current_db, set_current_db


class SalesCompanyItemTaxTests(TestCase):
    def test_validate_requires_sales_and_purchase_tax_when_company_sales(self):
        post = {"tax_pref": "taxable", "sales_tax": "10"}
        err = _validate_item_tax_selection(post, company_country="", company_tax_type="SALES")
        self.assertEqual(err, "Please select Purchase Tax Rate.")

        post = {"tax_pref": "taxable", "purchase_tax": "11"}
        err = _validate_item_tax_selection(post, company_country="", company_tax_type="SALES")
        self.assertEqual(err, "Please select Sales Tax Rate.")

        post = {
            "tax_pref": "taxable",
            "sales_tax": "10",
            "purchase_tax": "11",
        }
        err = _validate_item_tax_selection(post, company_country="", company_tax_type="SALES")
        self.assertIsNone(err)

    def test_assign_sets_sales_and_purchase_tax_for_sales_company(self):
        set_current_db("test_company")
        item = Item(name="Widget")
        post = {
            "tax_pref": "taxable",
            "sales_tax": "10",
            "purchase_tax": "11",
        }

        sales_obj = Tax(id=10, taxname="Sales Tax", rate="5.00", tax_scope="SALES")
        purchase_obj = Tax(id=11, taxname="Purchase Tax", rate="5.00", tax_scope="PURCHASE")

        def _fake_filter(id=None, **kwargs):
            q = MagicMock()
            if str(id) == "10":
                q.first.return_value = sales_obj
            elif str(id) == "11":
                q.first.return_value = purchase_obj
            else:
                q.first.return_value = None
            return q

        with patch("Items.views.Tax.objects.filter", side_effect=_fake_filter):
            _assign_item_tax_fields(item, post, company_country="", company_tax_type="SALES")

        clear_current_db()

        self.assertEqual(item.sales_tax_id, 10)
        self.assertEqual(item.purchase_tax_id, 11)
        self.assertIsNone(item.intra_tax_id)
        self.assertIsNone(item.inter_tax_group_id)
