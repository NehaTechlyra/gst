from django import forms
from django.test import SimpleTestCase

from stock.forms import StockAdjustmentForm, StockTransferForm


class StockNotesRequiredTests(SimpleTestCase):
    def test_stock_adjustment_requires_reason_and_notes(self):
        form = StockAdjustmentForm()
        with self.assertRaises(forms.ValidationError):
            form.fields['reason'].clean('')
        with self.assertRaises(forms.ValidationError):
            form.fields['notes'].clean('')

    def test_stock_transfer_requires_notes(self):
        form = StockTransferForm()
        with self.assertRaises(forms.ValidationError):
            form.fields['notes'].clean('   ')
