"""
eway_bill_api.py
~~~~~~~~~~~~~~~~
NIC E-Way Bill API integration service.

Supports:
  • Authentication  (GSTIN + username + password + app_key)
  • Generate EWB    (Part A + Part B in one call)
  • Cancel EWB
  • Update Vehicle  (Part B update)
  • Get EWB details (fetch by EWB number)

Usage
-----
    from .eway_bill_api import EWayBillAPI, EWayBillAPIError

    api    = EWayBillAPI.from_company(company)
    result = api.generate(eway_bill_instance)
    # result = {'ewbNo': '...',  'ewbDate': '...', 'validUpto': '...', ...}

Configuration (settings.py)
----------------------------
    EWAY_BILL_API = {
        "BASE_URL": "https://ewaybillgst.gov.in/BillGeneration/eway",      # sandbox
        # "BASE_URL": "https://gst.gov.in/bl/ewb",                          # production (rare)
        "SANDBOX": False,
    }

Per-company credentials are stored in EWayBillCredential model (see models section).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

import requests
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_Cipher
from Crypto.Util.Padding import pad, unpad
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .eway_bill_exceptions import (
    EWayBillAPIError,
    EWayBillAuthError,
    EWayBillValidationError,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SANDBOX_BASE_URL    = "https://ewaybillgst.gov.in/BillGeneration/eway"
PRODUCTION_BASE_URL = "https://gst.gov.in/bl/ewb"

CANCEL_REASONS = {
    "1": "Duplicate",
    "2": "Order Cancelled",
    "3": "Data Entry Mistake",
    "4": "Others",
}

SUPPLY_TYPE_MAP = {
    "B2B"  : "O",   # Outward supply
    "B2C"  : "O",
    "EXPWP": "E",   # Export with payment
    "EXPWOP": "EP", # Export without payment
}

# ─────────────────────────────────────────────────────────────────────────────
# Crypto helpers  (NIC uses AES-128 ECB + RSA public-key wrapping)
# ─────────────────────────────────────────────────────────────────────────────

class _NICCrypto:
    """Handles NIC-specific encrypt/decrypt for EWB API payloads."""

    @staticmethod
    def encrypt_app_key(app_key_bytes: bytes, nic_public_key_pem: str) -> str:
        """RSA-encrypt the AES app_key with the NIC public key → base64 string."""
        pub_key = RSA.import_key(nic_public_key_pem)
        cipher  = PKCS1_v1_5_Cipher.new(pub_key)
        encrypted = cipher.encrypt(app_key_bytes)
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def aes_encrypt(plaintext: str, app_key_bytes: bytes) -> str:
        """AES-128 ECB encrypt, PKCS7 padded → base64 string."""
        cipher     = AES.new(app_key_bytes[:16], AES.MODE_ECB)
        ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
        return base64.b64encode(ciphertext).decode()

    @staticmethod
    def aes_decrypt(ciphertext_b64: str, app_key_bytes: bytes) -> str:
        """AES-128 ECB decrypt base64 ciphertext → plaintext string."""
        cipher    = AES.new(app_key_bytes[:16], AES.MODE_ECB)
        decrypted = unpad(cipher.decrypt(base64.b64decode(ciphertext_b64)), AES.block_size)
        return decrypted.decode()


# ─────────────────────────────────────────────────────────────────────────────
# Auth token cache key
# ─────────────────────────────────────────────────────────────────────────────

def _token_cache_key(gstin: str) -> str:
    return f"ewb_token_{hashlib.md5(gstin.encode()).hexdigest()}"


# ─────────────────────────────────────────────────────────────────────────────
# EWayBillAPIConfig – runtime configuration (not the Django model)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EWayBillAPIConfig:
    """Runtime configuration object for API client."""
    gstin         : str
    username      : str
    password      : str
    app_key       : str          # 32-char random string; becomes AES session key
    nic_public_key: str          # NIC portal RSA public key (PEM format)
    base_url      : str = SANDBOX_BASE_URL
    sandbox       : bool = False


# ─────────────────────────────────────────────────────────────────────────────
# EWayBillAPI – main service class
# ─────────────────────────────────────────────────────────────────────────────

class EWayBillAPI:
    """
    High-level E-Way Bill API client.

    All network calls raise EWayBillAPIError (or subclasses) on failure.
    Successful responses return plain Python dicts.
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 1  # seconds

    def __init__(self, config: EWayBillAPIConfig):
        self.cfg      = config
        self._app_key = config.app_key.encode()[:16]   # 16 bytes for AES-128
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept"      : "application/json",
            "gstin"       : config.gstin,
            "user_name"   : config.username,
        })

    # ── factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_company(cls, company) -> "EWayBillAPI":
        """
        Build an EWayBillAPI instance from the Company's EWayBillCredential record.
        Raises EWayBillAuthError if credentials are not configured.
        """
        try:
            from .models import EWayBillCredential  # local import to avoid circular
            cred = EWayBillCredential.objects.get(company=company)
        except Exception as exc:
            raise EWayBillAuthError(
                "E-Way Bill API credentials not configured for this company. "
                "Go to Settings → E-Way Bill to add them."
            ) from exc

        ewb_settings = getattr(settings, "EWAY_BILL_API", {})
        base_url     = ewb_settings.get("BASE_URL", SANDBOX_BASE_URL)
        sandbox      = ewb_settings.get("SANDBOX", False)

        cfg = EWayBillAPIConfig(
            gstin          = cred.gstin,
            username       = cred.username,
            password       = cred.get_password(),
            app_key        = cred.app_key,
            nic_public_key = cred.nic_public_key,
            base_url       = base_url,
            sandbox        = sandbox,
        )
        return cls(cfg)

    # ── internals ─────────────────────────────────────────────────────────────

    def _get_auth_token(self) -> str:
        """
        Return a cached auth token, or authenticate fresh if expired/missing.
        NIC tokens are valid for 6 hours; we cache for 5 hours 50 minutes.
        """
        cache_key = _token_cache_key(self.cfg.gstin)
        token     = cache.get(cache_key)
        if token:
            return token

        token = self._authenticate()
        cache.set(cache_key, token, timeout=5 * 3600 + 50 * 60)
        return token

    def _authenticate(self) -> str:
        """
        Authenticate with NIC and return the auth token string.
        POST /authenticate
        """
        # Validate NIC public key before attempting encryption
        if not self.cfg.nic_public_key or not self.cfg.nic_public_key.strip():
            raise EWayBillAuthError(
                "NIC Public Key is missing. Download from https://ewaybillgst.gov.in/apidoc/ → API → Public Key."
            )
        if "-----BEGIN" not in self.cfg.nic_public_key:
            raise EWayBillAuthError(
                "NIC Public Key format is invalid. Must be PEM format starting with '-----BEGIN PUBLIC KEY-----'."
            )
        
        app_key_b64 = base64.b64encode(self._app_key).decode()
        try:
            encrypted_key = _NICCrypto.encrypt_app_key(
                self._app_key, self.cfg.nic_public_key
            )
        except ValueError as e:
            raise EWayBillAuthError(
                f"Failed to encrypt app key with NIC public key: {str(e)}. "
                "Verify the public key is valid PEM format."
            ) from e
        encrypted_pass = _NICCrypto.aes_encrypt(self.cfg.password, self._app_key)

        payload = {
            "action"  : "ACCESSTOKEN",
            "username": self.cfg.username,
            "password": encrypted_pass,
            "gstin"   : self.cfg.gstin,
            "app_key" : encrypted_key,
        }

        resp = self._post("/authenticate", payload, auth=False)

        # Decrypt returned token
        try:
            token_encrypted = resp["authToken"]
            token           = _NICCrypto.aes_decrypt(token_encrypted, self._app_key)
        except (KeyError, Exception) as exc:
            raise EWayBillAuthError(
                "Authentication succeeded but token decryption failed.",
                raw_response=resp
            ) from exc

        logger.info("EWB API: authenticated for GSTIN %s", self.cfg.gstin)
        return token

    def _post(self, endpoint: str, payload: dict, auth: bool = True) -> dict:
        """Make a POST request with retry logic; raise on HTTP or API errors."""
        url     = self.cfg.base_url.rstrip("/") + endpoint
        headers = {}
        if auth:
            headers["auth_token"] = self._get_auth_token()

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self._session.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Log successful request
                logger.debug(f"EWB API {endpoint} succeeded on attempt {attempt + 1}")
                self._check_api_error(data)
                return data

            except requests.Timeout as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"EWB API timeout (attempt {attempt + 1}, retrying...)")
                    continue
                raise EWayBillAPIError("Request to NIC timed out. Please retry.") from exc

            except requests.ConnectionError as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"EWB API connection error (attempt {attempt + 1}, retrying...)")
                    continue
                raise EWayBillAPIError("Could not reach NIC E-Way Bill server. Check connectivity.") from exc

            except requests.HTTPError as exc:
                raise EWayBillAPIError(f"HTTP {response.status_code}: {response.text[:300]}") from exc

            except ValueError as exc:
                raise EWayBillAPIError("Invalid JSON response from NIC server.") from exc

        raise last_error or EWayBillAPIError("Request failed after retries.")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request with retry logic."""
        url = self.cfg.base_url.rstrip("/") + endpoint
        headers = {"auth_token": self._get_auth_token()}
        
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self._session.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                self._check_api_error(data)
                return data
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"EWB API GET retry (attempt {attempt + 1})")
                    continue
                raise EWayBillAPIError(str(exc)) from exc

        raise last_error or EWayBillAPIError("GET request failed after retries.")

    @staticmethod
    def _check_api_error(data: dict):
        """Raise appropriate exception if NIC returned an error status."""
        status = data.get("status", "").upper()
        if status not in ("1", "SUCCESS", ""):
            error_codes = data.get("errorCodes", "")
            message     = data.get("message", data.get("messages", "Unknown API error"))
            if isinstance(message, list):
                message = "; ".join(m.get("message", "") for m in message)
            code = str(error_codes)
            if "106" in code or "auth" in message.lower():
                raise EWayBillAuthError(message, error_code=code, raw_response=data)
            if "error" in status.lower() or data.get("status") == "0":
                raise EWayBillValidationError(message, error_code=code, raw_response=data)
            if status not in ("1", "SUCCESS", ""):
                raise EWayBillAPIError(message, error_code=code, raw_response=data)

    # ── public API methods ────────────────────────────────────────────────────

    def generate(self, eway_bill) -> dict:
        """
        Generate an E-Way Bill from an EWayBill model instance.
        Returns the NIC response dict containing ewbNo, validUpto, etc.
        """
        payload = self._build_generate_payload(eway_bill)
        resp    = self._post("/generate", payload)
        return resp

    def cancel(self, ewb_number: str, reason_code: str = "2", remarks: str = "") -> dict:
        """
        Cancel an E-Way Bill by EWB number.
        reason_code: '1'=Duplicate, '2'=Order Cancelled, '3'=Data Entry Mistake, '4'=Others
        """
        payload = {
            "ewbNo"     : int(ewb_number),
            "cancelRsnCode": int(reason_code),
            "cancelRmrk": remarks or CANCEL_REASONS.get(reason_code, "Cancelled"),
        }
        resp = self._post("/cancel", payload)
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
        """Update Part B (vehicle details) of an existing EWB."""
        payload = {
            "ewbNo"       : int(ewb_number),
            "vehicleNo"   : vehicle_no.upper().replace(" ", ""),
            "fromPlace"   : from_place,
            "fromState"   : from_state,
            "reasonCode"  : "1",   # '1' = Due to Break Down
            "reasonRem"   : "Vehicle update",
            "transDocNo"  : trans_doc_no,
            "transDocDate": trans_doc_dt,
            "transMode"   : "1",
            "vehicleType" : vehicle_type,
        }
        resp = self._post("/updatevehicle", payload)
        return resp

    def get_by_number(self, ewb_number: str) -> dict:
        """Fetch E-Way Bill details by EWB number."""
        resp = self._get("/get", params={"ewbNo": ewb_number})
        return resp

    def test_connection(self) -> bool:
        """
        Test authentication with NIC API.
        Returns True if authentication succeeds.
        Raises EWayBillAuthError if credentials are invalid.
        """
        # Check if NIC public key is present and valid
        if not self.cfg.nic_public_key or not self.cfg.nic_public_key.strip():
            raise EWayBillAuthError(
                "NIC Public Key is missing. "
                "Download it from ewaybillgst.gov.in (API → Public Key) and paste it in the form."
            )
        
        if "-----BEGIN" not in self.cfg.nic_public_key or "-----END" not in self.cfg.nic_public_key:
            raise EWayBillAuthError(
                "NIC Public Key format is invalid. Must be a valid RSA PEM key. "
                "Download from ewaybillgst.gov.in (API → Public Key)."
            )
        
        try:
            token = self._get_auth_token()
            if token:
                logger.info("EWB API: test_connection succeeded for GSTIN %s", self.cfg.gstin)
                return True
        except EWayBillAuthError:
            raise
        except Exception as exc:
            logger.error("EWB API: test_connection failed: %s", exc)
            raise EWayBillAPIError(f"Connection test failed: {exc}") from exc

    # ── payload builder ───────────────────────────────────────────────────────

    def _build_generate_payload(self, bill) -> dict:
        """
        Map EWayBill model fields → NIC JSON payload.
        See NIC API spec: https://ewaybillgst.gov.in/apidoc/
        """
        invoice = bill.invoice
        items   = list(invoice.items.all().select_related("product"))

        # ── document details ────────────────────────────────────────────────
        doc_type = "INV"
        doc_dt   = invoice.date.strftime("%d/%m/%Y") if invoice.date else \
                   datetime.today().strftime("%d/%m/%Y")

        # ── tax totals from invoice items ───────────────────────────────────
        total_taxable = sum(
            Decimal(i.price or 0) * Decimal(i.quantity or 0) for i in items
        )
        cgst_amt  = sum(Decimal(getattr(i, "cgst_amount", 0) or 0) for i in items)
        sgst_amt  = sum(Decimal(getattr(i, "sgst_amount", 0) or 0) for i in items)
        igst_amt  = sum(Decimal(getattr(i, "igst_amount", 0) or 0) for i in items)
        cess_amt  = sum(Decimal(getattr(i, "cess_amount", 0) or 0) for i in items)

        # ── item list ───────────────────────────────────────────────────────
        item_list = []
        for idx, item in enumerate(items, start=1):
            qty     = float(item.quantity or 1)
            rate    = float(item.price or 0)
            taxable = round(qty * rate, 2)

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
                "taxableAmount": taxable,
            })

        # ── address details ─────────────────────────────────────────────────
        from_pincode = str(bill.pincode_from or "").strip() or "000000"
        to_pincode   = str(bill.pincode_to   or "").strip() or "000000"

        payload = {
            "supplyType"  : "O",    # Outward
            "subSupplyType": "1",   # Supply
            "docType"     : doc_type,
            "docNo"       : str(invoice.inv_number),
            "docDate"     : doc_dt,
            "fromGstin"   : bill.gstin_from or self.cfg.gstin,
            "fromTrdName" : self._company_name(invoice),
            "fromAddr1"   : getattr(invoice, "company_address", "") or "",
            "fromAddr2"   : "",
            "fromPlace"   : bill.place_from or "",
            "fromPincode" : int(from_pincode) if from_pincode.isdigit() else 0,
            "fromStateCode": self._state_code(bill.state_from),
            "actFromStateCode": self._state_code(bill.state_from),
            "toGstin"     : bill.gstin_to or "URP",  # URP = Unregistered Person
            "toTrdName"   : self._customer_name(invoice),
            "toAddr1"     : bill.place_to or "",
            "toAddr2"     : "",
            "toPlace"     : bill.place_to or "",
            "toPincode"   : int(to_pincode) if to_pincode.isdigit() else 0,
            "toStateCode" : self._state_code(bill.state_to),
            "actToStateCode": self._state_code(bill.state_to),
            "totalValue"  : float(bill.total_value),
            "cgstValue"   : float(cgst_amt),
            "sgstValue"   : float(sgst_amt),
            "igstValue"   : float(igst_amt),
            "cessValue"   : float(cess_amt),
            "cessNonAdvolValue": 0,
            "otherValue"  : 0,
            "totInvValue" : float(invoice.total_amount),
            "transMode"   : bill.mode_of_transport or "1",
            "transDistance": int(bill.approximate_distance or 0),
            "transporterName": bill.transporter_name or "",
            "transporterId"  : bill.transporter_id  or "",
            "transDocNo"  : bill.transport_doc_no or "",
            "transDocDate": bill.transport_doc_date.strftime("%d/%m/%Y") if bill.transport_doc_date else "",
            "vehicleNo"   : (bill.vehicle_number or "").upper().replace(" ", ""),
            "vehicleType" : bill.vehicle_type or "R",
            "itemList"    : item_list,
        }
        return payload

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _company_name(invoice) -> str:
        try:
            from company.models import Company
            co = Company.objects.filter(status=True).first() or Company.objects.first()
            return str(getattr(co, "company_name", "") or "")
        except Exception:
            return ""

    @staticmethod
    def _customer_name(invoice) -> str:
        cust = invoice.customer
        if not cust:
            return ""
        if getattr(cust, "customer_type", "") == "company":
            return str(getattr(cust, "company_name", "") or "")
        return f"{getattr(cust, 'first_name', '')} {getattr(cust, 'last_name', '')}".strip()

    # NIC state codes (2-digit numeric)
    _STATE_CODES: Dict[str, int] = {
        "jammu and kashmir": 1, "j&k": 1, "jk": 1,
        "himachal pradesh": 2, "hp": 2,
        "punjab": 3, "pb": 3,
        "chandigarh": 4,
        "uttarakhand": 5,
        "haryana": 6, "hr": 6,
        "delhi": 7, "nct of delhi": 7,
        "rajasthan": 8, "rj": 8,
        "uttar pradesh": 9, "up": 9,
        "bihar": 10,
        "sikkim": 11,
        "arunachal pradesh": 12,
        "nagaland": 13,
        "manipur": 14,
        "mizoram": 15,
        "tripura": 16,
        "meghalaya": 17,
        "assam": 18, "as": 18,
        "west bengal": 19, "wb": 19,
        "jharkhand": 20,
        "odisha": 21,
        "chhattisgarh": 22,
        "madhya pradesh": 23, "mp": 23,
        "gujarat": 24, "gj": 24,
        "daman and diu": 25,
        "dadra and nagar haveli": 26,
        "maharashtra": 27, "mh": 27,
        "andhra pradesh": 28, "ap": 28,
        "karnataka": 29, "ka": 29,
        "goa": 30, "ga": 30,
        "lakshadweep": 31,
        "kerala": 32, "kl": 32,
        "tamil nadu": 33, "tn": 33,
        "puducherry": 34,
        "andaman and nicobar": 35,
        "telangana": 36, "ts": 36, "tg": 36,
        "ladakh": 37,
        "other territory": 97,
        "other countries": 99,
    }

    def _state_code(self, state_str: str) -> int:
        """Convert state name/abbreviation to NIC 2-digit code."""
        if not state_str:
            return 0
        
        key = state_str.strip().lower()
        return self._STATE_CODES.get(key, 0)
