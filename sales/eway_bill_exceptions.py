"""
sales/eway_bill_exceptions.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Single source of truth for all E-Way Bill exceptions.
Import from here in ALL eway_bill_*.py files and views.
"""


class EWayBillAPIError(Exception):
    """Base exception for any E-Way Bill API failure."""
    def __init__(self, message: str, error_code: str = "", raw_response: dict = None):
        super().__init__(message)
        self.error_code   = error_code
        self.raw_response = raw_response or {}


class EWayBillAuthError(EWayBillAPIError):
    """Authentication failed — bad credentials, expired token, missing key."""
    pass


class EWayBillValidationError(EWayBillAPIError):
    """Payload rejected by NIC/GSP validation."""
    pass
