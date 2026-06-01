"""
sales/eway_bill_router.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Single import point. Use in ALL views:

    from .eway_bill_router import get_eway_api, EWayBillAPIError, EWayBillAuthError, EWayBillValidationError

Priority:
  1. EWAY_BILL_MOCK = True   →  local mock
  2. EWAY_BILL_GSP configured →  GSP (Masters India etc.)
  3. fallback                 →  direct NIC (EWayBillCredential in DB)
"""

from django.conf import settings

# Re-export from ONE shared location — so all except clauses in views catch the right class
from .eway_bill_exceptions import (
    EWayBillAPIError,
    EWayBillAuthError,
    EWayBillValidationError,
)



def get_eway_api():
    # 1. Mock
    if getattr(settings, "EWAY_BILL_MOCK", False):
        from .eway_bill_mock import EWayBillMock
        return EWayBillMock()

    # 2. GSP
    gsp_cfg = getattr(settings, "EWAY_BILL_GSP", None)
    if gsp_cfg and gsp_cfg.get("CLIENT_ID", "").strip():
        from .eway_bill_gsp import EWayBillGSP
        return EWayBillGSP.from_settings()

    # 3. Direct NIC
    from .eway_bill_api import EWayBillAPI
    from company.models import Company
    company = Company.objects.filter(status=True).first() or Company.objects.first()
    return EWayBillAPI.from_company(company)

