"""
Signal handlers for auto-creating draft E-Way Bills on invoice save.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import SalesInvoice, EWayBill


EWAY_THRESHOLD = 50000  # ₹50,000 – GST mandate threshold


# ✅ DISABLED: Auto E-Way Bill creation
# Users now must explicitly click "Generate E-Way Bill" button in the invoice detail page.
# If you want to re-enable auto-creation, uncomment the function below.
#
# @receiver(post_save, sender=SalesInvoice)
# def auto_create_eway_bill_draft(sender, instance, created, **kwargs):
#     """
#     Auto-create a draft E-Way Bill when a SalesInvoice ≥ ₹50,000 is created.
#     Only for Indian companies (checked via company.country).
#     DISABLED - Users should generate E-Way Bills manually via the Generate button.
#     """
#     if not created:
#         # Only on creation, not on edit
#         return
#     
#     # Check if invoice meets threshold
#     if instance.total_amount < EWAY_THRESHOLD:
#         return
#     
#     # Check if Indian company
#     try:
#         from company.models import Company
#         company = Company.objects.filter(status=True).first() or Company.objects.first()
#         if not company:
#             return
#         
#         # Simple check: if country is set and not India, skip
#         country_str = str(getattr(company, 'country', '') or '').lower()
#         if country_str and country_str != 'in':
#             return
#     except Exception:
#         pass
#     
#     # Check if EWayBill already exists for this invoice
#     if EWayBill.objects.filter(invoice=instance).exists():
#         return
#     
#     # Auto-fill from company and customer
#     try:
#         gstin_from = getattr(company, 'tax_id', '') or ''
#         place_from = getattr(company, 'city', '') or ''
#         pincode_from = getattr(company, 'postal_code', '') or ''
#         state_from = str(getattr(company, 'state', '') or '')
#         
#         gstin_to = getattr(instance.customer, 'gst_number', '') or ''
#         place_to = instance.shipping_city or getattr(instance.customer, 'city', '') or ''
#         pincode_to = instance.shipping_postal_code or getattr(instance.customer, 'postal_code', '') or ''
#         state_to = instance.shipping_state or instance.place_of_supply or ''
#         
#         # Get primary HSN from first invoice item
#         from .models import SalesInvoiceItem
#         first_item = SalesInvoiceItem.objects.filter(sales_inv=instance).order_by('id').first()
#         hsn_code = getattr(first_item, 'hsn_code', '') or ''
#         
#         # Create draft E-Way Bill
#         EWayBill.objects.create(
#             invoice=instance,
#             status='draft',
#             gstin_from=gstin_from,
#             place_from=place_from,
#             pincode_from=pincode_from,
#             state_from=state_from,
#             gstin_to=gstin_to,
#             place_to=place_to,
#             pincode_to=pincode_to,
#             state_to=state_to,
#             total_value=instance.total_amount,
#             hsn_code=hsn_code,
#         )
#     except Exception as e:
#         # Log but don't fail the invoice creation
#         import logging
#         logger = logging.getLogger(__name__)
#         logger.warning(f"Failed to auto-create EWayBill for invoice {instance.inv_number}: {e}")
