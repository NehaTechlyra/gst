"""
sales/eway_bill_mock.py
~~~~~~~~~~~~~~~~~~~~~~~
Local mock sandbox — no internet, no registration needed.
Enable with:  EWAY_BILL_MOCK = True  in settings.py
"""

from __future__ import annotations

import random
import string
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from .eway_bill_exceptions import (
    EWayBillAPIError,
    EWayBillAuthError,
    EWayBillValidationError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fake_ewb_number() -> str:
    """Generate a realistic 12-digit EWB number."""
    return "".join(random.choices(string.digits, k=12))


def _valid_upto_str(days: int = 1) -> str:
    """Return valid_upto string in NIC format: DD/MM/YYYY HH:MM:SS"""
    dt = timezone.now() + timedelta(days=days)
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _cache_key(ewb_no: str) -> str:
    return f"mock_ewb_{ewb_no}"


# ─────────────────────────────────────────────────────────────────────────────
# Mock client — same interface as EWayBillGSP / EWayBillAPI
# ─────────────────────────────────────────────────────────────────────────────

class EWayBillMock:
    """
    100% local mock of the NIC E-Way Bill API.
    Returns realistic fake responses without any network call.
    """

    PROVIDER = "mock_sandbox"

    # ── Public API (identical signatures to real clients) ─────────────────────

    def generate(self, eway_bill) -> dict:
        """
        Simulate EWB generation.
        Returns a realistic NIC-format response dict.
        """
        invoice = eway_bill.invoice

        # Validate minimum required fields (mirrors real NIC validation)
        errors = []
        if not eway_bill.gstin_from:
            errors.append("Supplier GSTIN (gstin_from) is required.")
        if not eway_bill.place_from:
            errors.append("From City (place_from) is required.")
        if not eway_bill.place_to:
            errors.append("Destination City (place_to) is required.")
        if not eway_bill.mode_of_transport:
            errors.append("Mode of transport is required.")
        if float(eway_bill.total_value or 0) < 50000:
            errors.append(
                f"Invoice value ₹{eway_bill.total_value} is below ₹50,000 threshold."
            )

        if errors:
            raise EWayBillValidationError(
                " | ".join(errors),
                error_code="MOCK_VALIDATION",
            )

        ewb_no     = _fake_ewb_number()
        valid_upto = _valid_upto_str(days=1)   # road < 100 km → 1 day

        resp = {
            "status"       : "1",
            "ewbNo"        : ewb_no,
            "ewbDate"      : timezone.now().strftime("%d/%m/%Y %H:%M:%S"),
            "validUpto"    : valid_upto,
            "alert"        : "⚙️ Mock Sandbox — not a real E-Way Bill",
            "docNo"        : str(invoice.inv_number),
            "fromGstin"    : eway_bill.gstin_from,
            "toGstin"      : eway_bill.gstin_to or "URP",
            "fromPlace"    : eway_bill.place_from,
            "toPlace"      : eway_bill.place_to,
            "transDistance": eway_bill.approximate_distance,
            "transMode"    : eway_bill.mode_of_transport,
            "vehicleNo"    : eway_bill.vehicle_number or "KA01AB1234",
            "totalValue"   : float(eway_bill.total_value),
            "cgstValue"    : 0,
            "sgstValue"    : 0,
            "igstValue"    : 0,
        }

        # Store in cache for refresh/get_by_number calls
        cache.set(_cache_key(ewb_no), resp, timeout=86400)

        return resp

    def cancel(self, ewb_number: str, reason_code: str = "2", remarks: str = "") -> dict:
        stored = cache.get(_cache_key(ewb_number))
        if stored and stored.get("status") == "0":
            raise EWayBillValidationError(
                f"EWB {ewb_number} is already cancelled.",
                error_code="MOCK_ALREADY_CANCELLED",
            )

        resp = {
            "status"        : "1",
            "cancelDate"    : timezone.now().strftime("%d/%m/%Y %H:%M:%S"),
            "ewbNo"         : ewb_number,
            "cancelRsnCode" : reason_code,
            "cancelRmrk"    : remarks or "Cancelled",
        }

        if stored:
            stored["status"] = "0"
            stored["cancelDate"] = resp["cancelDate"]
            cache.set(_cache_key(ewb_number), stored, timeout=86400)

        return resp

    def update_vehicle(
        self,
        ewb_number  : str,
        vehicle_no  : str,
        from_place  : str,
        from_state  : str,
        vehicle_type: str = "R",
        trans_doc_no: str = "",
        trans_doc_dt: str = "",
    ) -> dict:
        stored = cache.get(_cache_key(ewb_number))
        if stored:
            stored["vehicleNo"] = vehicle_no.upper()
            stored["validUpto"] = _valid_upto_str(days=1)
            cache.set(_cache_key(ewb_number), stored, timeout=86400)

        return {
            "status"    : "1",
            "ewbNo"     : ewb_number,
            "vehicleNo" : vehicle_no.upper(),
            "fromPlace" : from_place,
            "updateDate": timezone.now().strftime("%d/%m/%Y %H:%M:%S"),
            "validUpto" : _valid_upto_str(days=1),
        }

    def get_by_number(self, ewb_number: str) -> dict:
        stored = cache.get(_cache_key(ewb_number))
        if stored:
            return stored
        # Not found in cache — return minimal response
        return {
            "status" : "1",
            "ewbNo"  : ewb_number,
            "alert"  : "EWB not in mock cache (may have expired).",
        }

    def test_connection(self) -> bool:
        return True
