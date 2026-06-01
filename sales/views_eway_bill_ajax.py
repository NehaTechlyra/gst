"""
sales/views_eway_bill_ajax.py
NOTE: EWayBillCredentialForm has been MOVED to forms.py — it does not belong here.
"""

import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from company.models import Company
from .eway_bill_router import get_eway_api, EWayBillAPIError
from .permissions import can_view_eway_bill, can_edit_eway_bill
from .models import EWayBillCredential

logger = logging.getLogger(__name__)


def _current_company():
    return Company.objects.filter(status=True).first() or Company.objects.first()


@login_required
@require_POST
def eway_bill_test_connection(request):
    """Test API connection based on active mode.
    
    Mock Mode: Check that mock is active (no external call)
    GSP Mode: Test connection to GSP provider API (only if CLIENT_ID configured)
    Direct NIC Mode: Test connection to NIC with RSA key (only if RSA key exists)
    """
    # Permission check
    if not (getattr(request.user, 'is_superuser', False) or can_view_eway_bill(request.user) or can_edit_eway_bill(request.user)):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    from django.conf import settings
    
    # Determine active mode
    is_mock = getattr(settings, "EWAY_BILL_MOCK", False)
    gsp_cfg = getattr(settings, "EWAY_BILL_GSP", {}) or {}
    gsp_configured = bool(gsp_cfg.get("CLIENT_ID", "").strip())
    
    if is_mock:
        mode = "mock"
    elif gsp_configured:
        mode = "gsp"
    else:
        mode = "direct"
    
    # Mock Mode: Just confirm mock is active (no external call)
    if mode == "mock":
        return JsonResponse({
            "success": True,
            "message": "✓ Mock mode active — no external connection required",
            "mode": "mock",
        })
    
    # GSP Mode not fully configured
    if mode == "direct" and not is_mock and not gsp_configured:
        # Check if Direct NIC has RSA key
        try:
            cred = EWayBillCredential.objects.filter(
                company=_current_company()
            ).first()
            if not cred or not cred.nic_public_key:
                return JsonResponse({
                    "success": False,
                    "error": "❌ No API mode configured. Please either:\n1. Enable Mock mode for testing\n2. Configure GSP with CLIENT_ID\n3. Paste NIC RSA Public Key for Direct NIC",
                    "mode": "none"
                })
        except Exception:
            pass
    
    # GSP & Direct NIC: Test the actual connection
    try:
        api = get_eway_api()
        api.test_connection()
        if mode == "gsp":
            message = "✓ Connected to GSP provider successfully!"
        else:
            message = "✓ Connected to NIC (Direct) successfully!"
        return JsonResponse({
            "success": True,
            "message": message,
            "mode": mode,
        })
    except EWayBillAPIError as exc:
        return JsonResponse({
            "success": False, 
            "error": str(exc), 
            "mode": mode
        })
    except Exception as exc:
        logger.error("EWB test connection error: %s", exc)
        return JsonResponse({
            "success": False, 
            "error": "Unexpected error. Check server logs.", 
            "mode": mode
        })


@login_required
@require_POST
def eway_bill_regen_app_key(request):
    """Regenerate app_key for the current company. Returns JSON {app_key}."""
    # Permission check
    if not (getattr(request.user, 'is_superuser', False) or can_edit_eway_bill(request.user)):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    company = _current_company()
    try:
        cred = EWayBillCredential.objects.get(company=company)
        cred.regenerate_app_key()
        return JsonResponse({"app_key": cred.app_key})
    except EWayBillCredential.DoesNotExist:
        return JsonResponse({"error": "Credentials not found."}, status=404)
    except Exception as exc:
        logger.error("EWB regen app key error: %s", exc)
        return JsonResponse({"error": "Failed to regenerate app key."}, status=500)
