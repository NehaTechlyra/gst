"""
sales/views_eway_bill_api.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Final complete views — supports mock / GSP / direct NIC transparently.
Drop this in as your views_eway_bill_api.py (or merge into views.py).

Only import change from previous version:
    FROM: from .eway_bill_api import ...
    TO:   from .eway_bill_router import get_eway_api, EWayBillAPIError, ...
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .eway_bill_router import (
    get_eway_api,
    EWayBillAPIError,
    EWayBillAuthError,
    EWayBillValidationError,
)
from .permissions import (
    can_view_eway_bill,
    can_create_eway_bill,
    can_edit_eway_bill,
    can_delete_eway_bill,
)
from company.models import Company
from .models import (
    EWayBill,
    SalesInvoice,
    SalesInvoiceItem,
)

logger = logging.getLogger(__name__)
EWAY_THRESHOLD = 50_000


def _current_company():
    return Company.objects.filter(status=True).first() or Company.objects.first()


def _is_mock_mode():
    return getattr(settings, "EWAY_BILL_MOCK", False)


# ─────────────────────────────────────────────────────────────────────────────
# Generate / Edit
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def eway_bill_generate(request, invoice_id):
    from .forms import EWayBillForm
    from .views import redirect_with_company, _is_indian_company_country, _get_current_company_country

    invoice = get_object_or_404(SalesInvoice, pk=invoice_id)

    # Permission: require Create or Edit on E-Way Bill
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_eway_bill(request.user) or can_edit_eway_bill(request.user)):
            messages.error(request, 'You do not have permission to generate E-Way Bills.')
            return redirect_with_company('sales_inv_list')
    except Exception:
        messages.error(request, 'You do not have permission to generate E-Way Bills.')
        return redirect_with_company('sales_inv_list')

    if not _is_indian_company_country(_get_current_company_country(request)):
        messages.error(request, "E-Way Bill is only applicable for Indian companies.")
        return redirect_with_company("invoice_detail", pk=invoice_id)

    eway    = getattr(invoice, "eway_bill", None)
    company = _current_company()

    if request.method == "POST":
        form = EWayBillForm(request.POST, instance=eway)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.invoice     = invoice
            bill.total_value = invoice.total_amount
            bill.status      = "draft"

            # Auto-fill supplier side
            if not bill.gstin_from and company:
                bill.gstin_from   = getattr(company, "tax_id", "") or ""
            if not bill.place_from and company:
                bill.place_from   = getattr(company, "city", "") or ""
            if not bill.pincode_from and company:
                bill.pincode_from = getattr(company, "postal_code", "") or ""
            if not bill.state_from and company:
                bill.state_from   = str(getattr(company, "state", "") or "")

            # Auto-fill recipient side
            if not bill.gstin_to:
                bill.gstin_to = getattr(invoice.customer, "gst_number", "") or ""
            if not bill.state_to:
                bill.state_to = invoice.shipping_state or invoice.place_of_supply or ""
            if not bill.place_to:
                bill.place_to = (invoice.shipping_city
                                 or getattr(invoice.customer, "city", "") or "")
            if not bill.pincode_to:
                bill.pincode_to = (invoice.shipping_postal_code
                                   or getattr(invoice.customer, "postal_code", "") or "")

            # Primary HSN
            if not bill.hsn_code:
                first_item = SalesInvoiceItem.objects.filter(
                    sales_inv=invoice
                ).order_by("id").first()
                bill.hsn_code = getattr(first_item, "hsn_code", "") or ""

            bill.save()
            messages.success(request, f"E-Way Bill draft saved for Invoice {invoice.inv_number}.")

            # Call API (mock / GSP / direct)
            try:
                api  = get_eway_api()
                resp = api.generate(bill)

                ewb_no     = str(resp.get("ewbNo", "")).strip()
                valid_upto = resp.get("validUpto", "")
                alert      = resp.get("alert", "")

                bill.ewb_number   = ewb_no
                bill.status       = "generated"
                bill.generated_at = timezone.now()

                if hasattr(bill, "api_raw_response"):
                    bill.api_raw_response = resp
                if hasattr(bill, "alert"):
                    bill.alert = alert
                if hasattr(bill, "valid_upto") and valid_upto:
                    from datetime import datetime
                    try:
                        bill.valid_upto = datetime.strptime(valid_upto, "%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        pass

                bill.save()

                prefix = "🧪 [MOCK] " if _is_mock_mode() else ""
                msg = f"{prefix}E-Way Bill {ewb_no} generated successfully for Invoice {invoice.inv_number}."
                if alert and not _is_mock_mode():
                    msg += f" Note: {alert}"
                messages.success(request, msg)
                return redirect_with_company("eway_bill_detail", pk=bill.pk)

            except EWayBillAuthError as exc:
                error_msg = f"Mock error: {exc}" if _is_mock_mode() else \
                    f"Authentication failed: {exc}. Go to Settings → E-Way Bill to configure credentials."
                # Stay on form to show error immediately
                form = EWayBillForm(request.POST, instance=bill)
                return render(request, "sales/eway_bill_generate.html", {
                    "form"            : form,
                    "invoice"         : invoice,
                    "eway"            : bill,
                    "company_is_india": True,
                    "api_error"       : True,
                    "error_message"   : error_msg,
                    "mock_mode"       : _is_mock_mode(),
                })

            except EWayBillValidationError as exc:
                error_msg = f"Validation error: {exc}\n\nPlease fill in all required fields:\n• Company GSTIN (from company settings)\n• Company City (from company settings)\n• Transport Mode\n• Destination City & State"
                # Stay on form to show error immediately
                form = EWayBillForm(request.POST, instance=bill)
                return render(request, "sales/eway_bill_generate.html", {
                    "form"            : form,
                    "invoice"         : invoice,
                    "eway"            : bill,
                    "company_is_india": True,
                    "api_error"       : True,
                    "error_message"   : error_msg,
                    "mock_mode"       : _is_mock_mode(),
                })

            except EWayBillAPIError as exc:
                error_msg = f"API error: {exc}. Draft saved."
                # Stay on form to show error immediately
                form = EWayBillForm(request.POST, instance=bill)
                return render(request, "sales/eway_bill_generate.html", {
                    "form"            : form,
                    "invoice"         : invoice,
                    "eway"            : bill,
                    "company_is_india": True,
                    "api_error"       : True,
                    "error_message"   : error_msg,
                    "mock_mode"       : _is_mock_mode(),
                })
        else:
            # Form validation failed - display errors
            error_msgs = []
            for field, errors in form.errors.items():
                error_msgs.extend(errors)
            if error_msgs:
                messages.error(request, f"Form validation failed: {'; '.join(error_msgs)}")
            return render(request, "sales/eway_bill_generate.html", {
                "form"            : form,
                "invoice"         : invoice,
                "eway"            : eway,
                "company_is_india": True,
                "mock_mode"       : _is_mock_mode(),
            })
    else:
        initial = {}
        if not eway:
            initial = {
                "gstin_to"  : getattr(invoice.customer, "gst_number", "") or "",
                "place_to"  : (invoice.shipping_city
                               or getattr(invoice.customer, "city", "") or ""),
                "pincode_to": (invoice.shipping_postal_code
                               or getattr(invoice.customer, "postal_code", "") or ""),
                "state_to"  : invoice.shipping_state or invoice.place_of_supply or "",
            }
        form = EWayBillForm(instance=eway, initial=initial)

    return render(request, "sales/eway_bill_generate.html", {
        "form"            : form,
        "invoice"         : invoice,
        "eway"            : eway,
        "company_is_india": True,
        "mock_mode"       : _is_mock_mode(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cancel
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def eway_bill_cancel(request, pk):
    from .views import redirect_with_company

    bill    = get_object_or_404(EWayBill, pk=pk)

    # Permission: require Delete or Edit on E-Way Bill
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_eway_bill(request.user) or can_edit_eway_bill(request.user)):
            messages.error(request, 'You do not have permission to cancel E-Way Bills.')
            return redirect_with_company('eway_bill_detail', pk=pk)
    except Exception:
        messages.error(request, 'You do not have permission to cancel E-Way Bills.')
        return redirect_with_company('eway_bill_detail', pk=pk)

    if bill.status == "cancelled":
        messages.warning(request, "E-Way Bill is already cancelled.")
        return redirect_with_company("eway_bill_detail", pk=pk)

    reason_code = request.POST.get("cancel_reason", "2")
    remarks     = request.POST.get("cancel_remarks", "").strip()

    if bill.ewb_number and bill.status == "generated":
        try:
            api  = get_eway_api()
            resp = api.cancel(bill.ewb_number, reason_code=reason_code, remarks=remarks)
            logger.info("EWB %s cancelled. Mock=%s resp=%s", bill.ewb_number, _is_mock_mode(), resp)
        except EWayBillAPIError as exc:
            messages.error(request, f"Cancellation failed: {exc}")
            return redirect_with_company("eway_bill_detail", pk=pk)

    if hasattr(bill, "cancel_reason_code"):
        bill.cancel_reason_code = reason_code
    if hasattr(bill, "cancel_remarks"):
        bill.cancel_remarks = remarks

    bill.status = "cancelled"
    bill.save()

    prefix = "🧪 [MOCK] " if _is_mock_mode() else ""
    messages.success(
        request,
        f"{prefix}E-Way Bill {bill.ewb_number or '(draft)'} cancelled successfully."
    )
    return redirect_with_company("eway_bill_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# Update Vehicle
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def eway_bill_update_vehicle(request, pk):
    from .views import redirect_with_company

    bill       = get_object_or_404(EWayBill, pk=pk)

    # Permission: require Edit on E-Way Bill
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_eway_bill(request.user)):
            messages.error(request, 'You do not have permission to update vehicle details.')
            return redirect_with_company('eway_bill_detail', pk=pk)
    except Exception:
        messages.error(request, 'You do not have permission to update vehicle details.')
        return redirect_with_company('eway_bill_detail', pk=pk)

    vehicle_no = request.POST.get("vehicle_number", "").strip()

    if not vehicle_no:
        messages.error(request, "Vehicle number is required.")
        return redirect_with_company("eway_bill_detail", pk=pk)

    if not bill.ewb_number or bill.status != "generated":
        messages.error(request, "Vehicle update is only possible for generated E-Way Bills.")
        return redirect_with_company("eway_bill_detail", pk=pk)

    try:
        api  = get_eway_api()
        resp = api.update_vehicle(
            ewb_number   = bill.ewb_number,
            vehicle_no   = vehicle_no,
            from_place   = bill.place_from,
            from_state   = bill.state_from,
            vehicle_type = bill.vehicle_type,
        )
        bill.vehicle_number = vehicle_no
        bill.save(update_fields=["vehicle_number"])
        prefix = "🧪 [MOCK] " if _is_mock_mode() else ""
        messages.success(request, f"{prefix}Vehicle updated to {vehicle_no}.")
    except EWayBillAPIError as exc:
        messages.error(request, f"Vehicle update failed: {exc}")

    return redirect_with_company("eway_bill_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# Refresh
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def eway_bill_refresh(request, pk):
    from .views import redirect_with_company

    bill = get_object_or_404(EWayBill, pk=pk)

    # Permission: require View or Edit on E-Way Bill
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_eway_bill(request.user) or can_edit_eway_bill(request.user)):
            messages.error(request, 'You do not have permission to refresh E-Way Bills.')
            return redirect_with_company('eway_bill_detail', pk=pk)
    except Exception:
        messages.error(request, 'You do not have permission to refresh E-Way Bills.')
        return redirect_with_company('eway_bill_detail', pk=pk)

    if not bill.ewb_number:
        messages.error(request, "No EWB number to refresh.")
        return redirect_with_company("eway_bill_detail", pk=pk)

    try:
        api  = get_eway_api()
        resp = api.get_by_number(bill.ewb_number)
        if hasattr(bill, "api_raw_response"):
            bill.api_raw_response = resp
        bill.save()
        prefix = "🧪 [MOCK] " if _is_mock_mode() else ""
        messages.success(request, f"{prefix}E-Way Bill refreshed.")
    except EWayBillAPIError as exc:
        messages.error(request, f"Refresh failed: {exc}")

    return redirect_with_company("eway_bill_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# Credentials page (shows mock banner when mock mode is on)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def eway_bill_credentials(request):
    from .forms import EWayBillCredentialForm
    from .views import redirect_with_company

    # Permission: require View or Edit on E-Way Bill
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_eway_bill(request.user) or can_edit_eway_bill(request.user)):
            messages.error(request, 'You do not have permission to access E-Way Bill credentials.')
            return redirect_with_company('sales_dashboard')
    except Exception:
        messages.error(request, 'You do not have permission to access E-Way Bill credentials.')
        return redirect_with_company('sales_dashboard')

    company = _current_company()
    if not company:
        messages.error(request, "No company found.")
        return redirect_with_company("dashboard")

    try:
        from .models import EWayBillCredential
        cred, _ = EWayBillCredential.objects.get_or_create(
            company=company,
            defaults={"gstin": getattr(company, "tax_id", "") or ""},
        )
    except Exception:
        cred = None

    gsp_cfg      = getattr(settings, "EWAY_BILL_GSP", {}) or {}
    mock_mode    = _is_mock_mode()
    gsp_provider = gsp_cfg.get("PROVIDER", "masters_india")
    gsp_client_id= gsp_cfg.get("CLIENT_ID", "")
    gsp_gstin    = gsp_cfg.get("GSTIN", "")
    gsp_username = gsp_cfg.get("USERNAME", "")
    gsp_sandbox  = gsp_cfg.get("SANDBOX", True)
    
    # Determine active API mode for button label
    # Check if GSP is actually configured (CLIENT_ID with value)
    gsp_is_configured = bool(gsp_client_id and gsp_client_id.strip())
    
    if mock_mode:
        active_mode = "mock"
    elif gsp_is_configured:
        active_mode = "gsp"
    else:
        active_mode = "direct"

    if request.method == "POST" and cred:
        form = EWayBillCredentialForm(request.POST, instance=cred, mock_mode=mock_mode)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                raw_pass = form.cleaned_data.get("password_raw", "").strip()
                
                # Handle password
                if raw_pass:
                    obj.set_password(raw_pass)
                # if blank → keep existing encrypted password, do nothing
                
                obj.save()
                msg = "✓ Settings saved (Mock mode enabled)." if mock_mode else "✓ Credentials saved."
                messages.success(request, msg)
                # Add query param to force page reload
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(request.path + "?saved=1")
            except Exception as exc:
                logger.error(f"Error saving credentials: {exc}")
                messages.error(request, f"Failed to save: {str(exc)}")
        else:
            # Log form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            logger.error(f"Form validation errors: {form.errors}")
    else:
        form = EWayBillCredentialForm(instance=cred, mock_mode=mock_mode) if cred else None

    return render(request, "sales/eway_bill_credentials.html", {
        "form"            : form,
        "company"         : company,
        "cred"            : cred,
        "mock_mode"       : mock_mode,
        "active_mode"     : active_mode,
        "gsp_provider"    : gsp_provider,
        "gsp_client_id"   : gsp_client_id,
        "gsp_gstin"       : gsp_gstin,
        "gsp_username"    : gsp_username,
        "gsp_sandbox"     : gsp_sandbox,
        "gsp_configured"  : gsp_is_configured,
        "direct_configured": bool(cred and cred.gstin) if cred else False,
    })
