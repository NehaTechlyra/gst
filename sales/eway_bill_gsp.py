"""
eway_bill_gsp.py
~~~~~~~~~~~~~~~~
GSP (GST Suvidha Provider) adapter for E-Way Bill API.

Replaces direct NIC API calls with GSP middleware calls.
GSP handles NIC authentication on your behalf — NO 25,000 invoice
requirement, NO RSA key encryption needed.

Supported GSPs (uncomment the one you sign up with):
  • Masters India  – https://einvoice1.gst.gov.in (most popular, good docs)
  • Clear (ClearTax)
  • Karza
  • Any NIC-authorized GSP

Typical GSP flow:
  1. Register at GSP portal → get client_id + client_secret
  2. Call GSP auth endpoint → get gstin_token
  3. Call GSP EWB endpoints with gstin_token in header
  4. GSP forwards to NIC and returns response

Setup:
  pip install requests

settings.py additions:
  EWAY_BILL_GSP = {
      "PROVIDER"     : "masters_india",     # or "cleartax", "karza"
      "CLIENT_ID"    : "your_client_id",
      "CLIENT_SECRET": "your_client_secret",
      "GSTIN"        : "29AAAAA0000A1Z5",
      "USERNAME"     : "your_ewb_portal_username",
      "PASSWORD"     : "your_ewb_portal_password",
      "SANDBOX"      : True,    # False for production
  }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GSP provider configurations
# ─────────────────────────────────────────────────────────────────────────────

GSP_CONFIGS = {
    "masters_india": {
        "sandbox_url" : "https://sample-einvoice.masterspro.in/ewaybill/v3",
        "prod_url"    : "https://einvoice.masterspro.in/ewaybill/v3",
        "auth_path"   : "/authenticate",
        "generate_path": "/generate",
        "cancel_path" : "/cancel",
        "vehicle_path": "/updatevehicle",
        "get_path"    : "/get",
        "auth_type"   : "masters",        # proprietary auth flow
    },
    "cleartax": {
        "sandbox_url" : "https://sandbox.clear.in/ewb/v1",
        "prod_url"    : "https://api.clear.in/ewb/v1",
        "auth_path"   : "/sessions",
        "generate_path": "/ewaybills",
        "cancel_path" : "/ewaybills/cancel",
        "vehicle_path": "/ewaybills/updatevehicle",
        "get_path"    : "/ewaybills",
        "auth_type"   : "cleartax",
    },
    "karza": {
        "sandbox_url" : "https://testapi.karza.in/v3/ewb",
        "prod_url"    : "https://api.karza.in/v3/ewb",
        "auth_path"   : "/auth",
        "generate_path": "/generate",
        "cancel_path" : "/cancel",
        "vehicle_path": "/updatevehicle",
        "get_path"    : "/get",
        "auth_type"   : "karza",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions (import from shared location)
# ─────────────────────────────────────────────────────────────────────────────

from .eway_bill_exceptions import (
    EWayBillAPIError,
    EWayBillAuthError,
    EWayBillValidationError,
)


# ─────────────────────────────────────────────────────────────────────────────
# GSP Client
# ─────────────────────────────────────────────────────────────────────────────

class EWayBillGSP:
    """
    GSP-based E-Way Bill client.
    Works for ANY taxpayer — no invoice volume requirement.
    """

    def __init__(self):
        cfg = getattr(settings, "EWAY_BILL_GSP", {})
        if not cfg:
            raise EWayBillAuthError(
                "EWAY_BILL_GSP not configured in settings.py. "
                "Add GSP credentials to use E-Way Bill API."
            )

        self.provider      = cfg.get("PROVIDER", "masters_india").lower()
        self.client_id     = cfg["CLIENT_ID"]
        self.client_secret = cfg["CLIENT_SECRET"]
        self.gstin         = cfg["GSTIN"]
        self.username      = cfg["USERNAME"]
        self.password      = cfg["PASSWORD"]
        self.sandbox       = cfg.get("SANDBOX", True)

        if self.provider not in GSP_CONFIGS:
            raise EWayBillAuthError(
                f"Unknown GSP provider '{self.provider}'. "
                f"Choose from: {list(GSP_CONFIGS.keys())}"
            )

        gsp = GSP_CONFIGS[self.provider]
        self.base_url = gsp["sandbox_url"] if self.sandbox else gsp["prod_url"]
        self._paths   = gsp
        self._auth_type = gsp["auth_type"]

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_settings(cls) -> "EWayBillGSP":
        return cls()

    # ── Auth token management ─────────────────────────────────────────────────

    def _cache_key(self) -> str:
        import hashlib
        return f"ewb_gsp_token_{hashlib.md5(self.gstin.encode()).hexdigest()}"

    def _get_token(self) -> str:
        token = cache.get(self._cache_key())
        if token:
            return token
        token = self._authenticate()
        cache.set(self._cache_key(), token, timeout=5 * 3600 + 50 * 60)
        return token

    def _authenticate(self) -> str:
        """Auth varies slightly by GSP — all return a bearer/session token."""
        if self._auth_type == "masters":
            return self._auth_masters()
        elif self._auth_type == "cleartax":
            return self._auth_cleartax()
        elif self._auth_type == "karza":
            return self._auth_karza()
        else:
            raise EWayBillAuthError(f"Unknown auth type: {self._auth_type}")

    def _auth_masters(self) -> str:
        """Masters India auth: POST /authenticate with GSTIN + credentials."""
        url = self.base_url + self._paths["auth_path"]
        payload = {
            "action"       : "ACCESSTOKEN",
            "clientid"     : self.client_id,
            "clientsecret" : self.client_secret,
            "gstin"        : self.gstin,
            "username"     : self.username,
            "password"     : self.password,
        }
        resp = self._raw_post(url, payload)
        token = (
            resp.get("authToken")
            or resp.get("data", {}).get("authToken")
            or resp.get("token")
        )
        if not token:
            raise EWayBillAuthError(
                "Masters India auth: no token in response.",
                raw_response=resp
            )
        logger.info("EWB GSP (Masters India): authenticated for %s", self.gstin)
        return token

    def _auth_cleartax(self) -> str:
        """ClearTax auth: POST /sessions."""
        url = self.base_url + self._paths["auth_path"]
        payload = {
            "clientId"    : self.client_id,
            "clientSecret": self.client_secret,
            "gstin"       : self.gstin,
            "username"    : self.username,
            "password"    : self.password,
        }
        resp = self._raw_post(url, payload)
        token = resp.get("sessionToken") or resp.get("token") or resp.get("access_token")
        if not token:
            raise EWayBillAuthError("ClearTax auth: no token returned.", raw_response=resp)
        return token

    def _auth_karza(self) -> str:
        """Karza auth: POST /auth with API key."""
        url = self.base_url + self._paths["auth_path"]
        payload = {
            "x-karza-key": self.client_secret,
            "gstin"      : self.gstin,
            "username"   : self.username,
            "password"   : self.password,
        }
        resp = self._raw_post(url, payload)
        token = resp.get("result", {}).get("token") or resp.get("token")
        if not token:
            raise EWayBillAuthError("Karza auth: no token returned.", raw_response=resp)
        return token

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _raw_post(self, url: str, payload: dict) -> dict:
        try:
            r = self._session.post(url, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            raise EWayBillAPIError("GSP request timed out.")
        except requests.ConnectionError:
            raise EWayBillAPIError("Cannot reach GSP server.")
        except requests.HTTPError as e:
            raise EWayBillAPIError(f"HTTP {r.status_code}: {r.text[:200]}") from e
        except ValueError:
            raise EWayBillAPIError("Invalid JSON from GSP.")

    def _post(self, path: str, payload: dict) -> dict:
        url = self.base_url + path
        token = self._get_token()
        headers = self._auth_headers(token)
        try:
            r = self._session.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.Timeout:
            raise EWayBillAPIError("GSP request timed out.")
        except requests.ConnectionError:
            raise EWayBillAPIError("Cannot reach GSP server.")
        except requests.HTTPError as e:
            raise EWayBillAPIError(f"HTTP {r.status_code}: {r.text[:200]}") from e
        except ValueError:
            raise EWayBillAPIError("Invalid JSON from GSP.")
        self._check_error(data)
        return data

    def _get(self, path: str, params: dict = None) -> dict:
        url = self.base_url + path
        token = self._get_token()
        headers = self._auth_headers(token)
        try:
            r = self._session.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            raise EWayBillAPIError(str(e)) from e
        self._check_error(data)
        return data

    def _auth_headers(self, token: str) -> dict:
        """Each GSP uses slightly different header names."""
        if self._auth_type == "masters":
            return {
                "authtoken"   : token,
                "gstin"       : self.gstin,
                "user_name"   : self.username,
                "clientid"    : self.client_id,
                "clientsecret": self.client_secret,
            }
        elif self._auth_type == "cleartax":
            return {
                "x-cleartax-auth-token": token,
                "gstin": self.gstin,
            }
        elif self._auth_type == "karza":
            return {
                "Authorization": f"Bearer {token}",
                "x-karza-key"  : self.client_secret,
                "gstin"        : self.gstin,
            }
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _check_error(data: dict):
        status = str(data.get("status", "1"))
        if status in ("0", "error", "ERROR"):
            msg = data.get("message") or data.get("errorMessage") or "GSP API error"
            code = str(data.get("errorCode") or data.get("errorCodes", ""))
            if "auth" in msg.lower() or "token" in msg.lower() or "106" in code:
                raise EWayBillAuthError(msg, error_code=code, raw_response=data)
            raise EWayBillValidationError(msg, error_code=code, raw_response=data)

    # ── Public API methods (same interface as EWayBillAPI) ────────────────────

    def generate(self, eway_bill) -> dict:
        payload = self._build_payload(eway_bill)
        return self._post(self._paths["generate_path"], payload)

    def cancel(self, ewb_number: str, reason_code: str = "2", remarks: str = "") -> dict:
        payload = {
            "ewbNo"         : int(ewb_number),
            "cancelRsnCode" : int(reason_code),
            "cancelRmrk"    : remarks or "Cancelled",
        }
        return self._post(self._paths["cancel_path"], payload)

    def update_vehicle(self, ewb_number, vehicle_no, from_place,
                       from_state, vehicle_type="R",
                       trans_doc_no="", trans_doc_dt="") -> dict:
        payload = {
            "ewbNo"       : int(ewb_number),
            "vehicleNo"   : vehicle_no.upper().replace(" ", ""),
            "fromPlace"   : from_place,
            "fromState"   : from_state,
            "reasonCode"  : "1",
            "reasonRem"   : "Vehicle update",
            "transDocNo"  : trans_doc_no,
            "transDocDate": trans_doc_dt,
            "transMode"   : "1",
            "vehicleType" : vehicle_type,
        }
        return self._post(self._paths["vehicle_path"], payload)

    def get_by_number(self, ewb_number: str) -> dict:
        return self._get(self._paths["get_path"], params={"ewbNo": ewb_number})

    def test_connection(self) -> bool:
        """Returns True if auth succeeds. Raises EWayBillAuthError on failure."""
        cache.delete(self._cache_key())
        self._authenticate()
        return True

    # ── Payload builder ───────────────────────────────────────────────────────

    def _build_payload(self, bill) -> dict:
        """Build NIC-format JSON payload from EWayBill model instance."""
        from .models import SalesInvoiceItem
        from company.models import Company

        invoice = bill.invoice
        items   = list(SalesInvoiceItem.objects.filter(sales_inv=invoice).select_related("product"))

        doc_dt = (invoice.date.strftime("%d/%m/%Y")
                  if invoice.date else
                  timezone.now().strftime("%d/%m/%Y"))

        total_taxable = sum((getattr(i, "price", 0) or 0) *
                            (getattr(i, "quantity", 0) or 0) for i in items)
        cgst_amt = sum(getattr(i, "cgst_amount", 0) or 0 for i in items)
        sgst_amt = sum(getattr(i, "sgst_amount", 0) or 0 for i in items)
        igst_amt = sum(getattr(i, "igst_amount", 0) or 0 for i in items)
        cess_amt = sum(getattr(i, "cess_amount", 0) or 0 for i in items)

        item_list = []
        for idx, item in enumerate(items, 1):
            qty     = float(getattr(item, "quantity", 1) or 1)
            rate    = float(getattr(item, "price", 0) or 0)
            item_list.append({
                "itemNo"      : idx,
                "productName" : getattr(item, "product_name", "") or str(item),
                "productDesc" : getattr(item, "description", "") or "",
                "hsnCode"     : str(getattr(item, "hsn_code", "") or ""),
                "quantity"    : qty,
                "qtyUnit"     : "NOS",
                "cgstRate"    : float(getattr(item, "cgst_rate", 0) or 0),
                "sgstRate"    : float(getattr(item, "sgst_rate", 0) or 0),
                "igstRate"    : float(getattr(item, "igst_rate", 0) or 0),
                "cessRate"    : float(getattr(item, "cess_rate", 0) or 0),
                "cessNonAdvol": 0,
                "taxableAmount": round(qty * rate, 2),
            })

        from_pin = str(bill.pincode_from or "").strip()
        to_pin   = str(bill.pincode_to   or "").strip()

        try:
            co = Company.objects.filter(status=True).first() or Company.objects.first()
            co_name = str(getattr(co, "company_name", "") or "")
        except Exception:
            co_name = ""

        cust = invoice.customer
        if cust:
            cust_name = (str(getattr(cust, "company_name", "") or "")
                         if getattr(cust, "customer_type", "") == "company"
                         else f"{getattr(cust, 'first_name', '')} {getattr(cust, 'last_name', '')}".strip())
        else:
            cust_name = ""

        return {
            "supplyType"      : "O",
            "subSupplyType"   : "1",
            "docType"         : "INV",
            "docNo"           : str(invoice.inv_number),
            "docDate"         : doc_dt,
            "fromGstin"       : bill.gstin_from or self.gstin,
            "fromTrdName"     : co_name,
            "fromAddr1"       : getattr(invoice, "company_address", "") or "",
            "fromAddr2"       : "",
            "fromPlace"       : bill.place_from or "",
            "fromPincode"     : int(from_pin) if from_pin.isdigit() else 0,
            "fromStateCode"   : _state_code(bill.state_from),
            "actFromStateCode": _state_code(bill.state_from),
            "toGstin"         : bill.gstin_to or "URP",
            "toTrdName"       : cust_name,
            "toAddr1"         : bill.place_to or "",
            "toAddr2"         : "",
            "toPlace"         : bill.place_to or "",
            "toPincode"       : int(to_pin) if to_pin.isdigit() else 0,
            "toStateCode"     : _state_code(bill.state_to),
            "actToStateCode"  : _state_code(bill.state_to),
            "totalValue"      : float(bill.total_value),
            "cgstValue"       : float(cgst_amt),
            "sgstValue"       : float(sgst_amt),
            "igstValue"       : float(igst_amt),
            "cessValue"       : float(cess_amt),
            "cessNonAdvolValue": 0,
            "otherValue"      : 0,
            "totInvValue"     : float(invoice.total_amount),
            "transMode"       : bill.mode_of_transport or "1",
            "transDistance"   : int(bill.approximate_distance or 0),
            "transporterName" : bill.transporter_name or "",
            "transporterId"   : bill.transporter_id   or "",
            "transDocNo"      : bill.transport_doc_no  or "",
            "transDocDate"    : (bill.transport_doc_date.strftime("%d/%m/%Y")
                                 if bill.transport_doc_date else ""),
            "vehicleNo"       : (bill.vehicle_number or "").upper().replace(" ", ""),
            "vehicleType"     : bill.vehicle_type or "R",
            "itemList"        : item_list,
        }


# ─────────────────────────────────────────────────────────────────────────────
# State code helper
# ─────────────────────────────────────────────────────────────────────────────

_STATE_MAP = {
    "jammu and kashmir":1,"j&k":1,"jk":1,"himachal pradesh":2,"hp":2,
    "punjab":3,"pb":3,"chandigarh":4,"uttarakhand":5,"haryana":6,"hr":6,
    "delhi":7,"rajasthan":8,"rj":8,"uttar pradesh":9,"up":9,"bihar":10,
    "sikkim":11,"arunachal pradesh":12,"nagaland":13,"manipur":14,
    "mizoram":15,"tripura":16,"meghalaya":17,"assam":18,"as":18,
    "west bengal":19,"wb":19,"jharkhand":20,"odisha":21,"chhattisgarh":22,
    "madhya pradesh":23,"mp":23,"gujarat":24,"gj":24,"daman and diu":25,
    "dadra and nagar haveli":26,"maharashtra":27,"mh":27,
    "andhra pradesh":28,"ap":28,"karnataka":29,"ka":29,
    "goa":30,"ga":30,"lakshadweep":31,"kerala":32,"kl":32,
    "tamil nadu":33,"tn":33,"puducherry":34,"andaman and nicobar":35,
    "telangana":36,"ts":36,"ladakh":37,"other territory":97,"other countries":99,
}

def _state_code(state_str: str) -> int:
    if not state_str:
        return 0
    s = state_str.strip()
    if s[:2].isdigit():
        return int(s[:2])
    return _STATE_MAP.get(s.lower(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# Drop-in replacement: get_eway_api()
# Use this in views instead of EWayBillAPI.from_company()
# ─────────────────────────────────────────────────────────────────────────────


