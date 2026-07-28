"""
MIDDLEWARE - Company Registration Flow - FIXED
Properly exempts ALL company setup endpoints including POST requests

VERSION: 4.0 - CRITICAL FIX for 405 Method Not Allowed
ISSUE: Middleware was not properly exempting POST requests to company setup API endpoints
FIX: Moved company setup exemption to the VERY TOP of middleware chain
     with comprehensive path matching

DATE: 2026-02-13
"""

from django.shortcuts import redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.urls import resolve
from company.models import Company
import logging
import re

logger = logging.getLogger(__name__)

ADMIN_PATH_REGEX = re.compile(r'^/(?:[A-Z0-9-]+/)?admin(?:/|$)')


class RegistrationFlowMiddleware:
    """
    Middleware to handle first-time company registration.
    
    CRITICAL FIX: Company setup paths must be checked FIRST and COMPLETELY EXEMPT
    from all other middleware logic, regardless of GET/POST method.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # =====================================================
        # CRITICAL: COMPANY SETUP - CHECK THIS FIRST!
        # Must be at the TOP of all middleware checks
        # =====================================================
        
        # Define all company setup paths (both with and without company_code prefix)
        if self._is_company_setup_path(request.path):
            logger.info(f"[REG FLOW] ✅✅✅ COMPANY SETUP PATH DETECTED - COMPLETE BYPASS: {request.path} [{request.method}]")
            return self.get_response(request)
        
        # =====================================================
        # Standard exemptions - Static/Media/Admin
        # =====================================================
        exempt_paths = [
            '/static/',
            '/media/',
            '/admin/',
        ]
        
        if ADMIN_PATH_REGEX.match(request.path) or any(request.path.startswith(path) for path in exempt_paths):
            logger.debug(f"[REG FLOW] ✅ EXEMPT PATH: {request.path}")
            return self.get_response(request)
        
        # =====================================================
        # Auth pages - Always allow
        # =====================================================
        auth_paths = [
            '/Signup/',
            '/signup/',
            '/login/',
            '/logout/',
            '/check-username/',
            '/check-email/',
        ]
        
        if any(request.path.startswith(path) for path in auth_paths):
            logger.debug(f"[REG FLOW] ✅ AUTH PATH: {request.path}")
            return self.get_response(request)
        
        # =====================================================
        # Unauthenticated users - Allow (login page handles)
        # =====================================================
        if not request.user.is_authenticated:
            logger.debug(f"[REG FLOW] User not authenticated")
            return self.get_response(request)
        
        # =====================================================
        # Superuser bypass
        # =====================================================
        if request.user.is_superuser:
            logger.debug(f"[REG FLOW] ✅ Superuser bypass")
            return self.get_response(request)
        
        # =====================================================
        # Users in setup flow - Allow
        # =====================================================
        setup_company_id = request.session.get('setup_company_id')
        company_id = request.session.get('company_id')
        
        if setup_company_id or company_id:
            logger.debug(f"[REG FLOW] ✅ User in setup flow (company_id: {setup_company_id or company_id})")
            return self.get_response(request)
        
        # =====================================================
        # Check if company exists (for regular users)
        # =====================================================
        company_exists = Company.objects.exists()
        
        if not company_exists:
            logger.info(f"[REG FLOW] ⚠️ No company exists, redirecting to setup")
            if not self._is_company_setup_path(request.path):
                return redirect_with_company('company_registration')
        
        logger.debug(f"[REG FLOW] ✅ Continuing normally")
        return self.get_response(request)
    
    def _is_company_setup_path(self, path):
        """
        Check if path is a company setup path.
        Handles both direct paths and company_code prefixed paths.
        
        Examples that should match:
        - /company/setup/
        - /company/setup/company-info/
        - /company/setup/license-activation/
        - /company/setup/complete/
        - /company/setup/status/
        - /TECHKQK30J3A/company/setup/
        - /TECHKQK30J3A/company/setup/company-info/
        
        Returns:
            bool: True if path is a company setup path
        """
        # List of all company setup endpoints
        setup_paths = [
            '/company/setup/',
            '/company/setup/company-info/',
            '/company/setup/fiscal-year/',
            '/company/setup/license-activation/',
            '/company/setup/complete/',
            '/company/setup/status/',
        ]
        
        # Check direct path match
        if any(path.startswith(setup_path) for setup_path in setup_paths):
            return True
        
        # Check company_code prefixed path match
        # Pattern: /COMPANY_CODE/company/setup/...
        # Company codes are typically uppercase alphanumeric with hyphens
        if re.match(r'^/[A-Z0-9-]+/company/setup/', path):
            return True
        
        return False


class RegistrationCompletionMiddleware:
    """
    Ensures registration steps are completed in order.
    
    CRITICAL FIX: Company setup API endpoints are COMPLETELY EXEMPT
    VERSION: 4.0 - Fixed to properly handle POST requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # =====================================================
        # CRITICAL: COMPANY SETUP API - CHECK FIRST!
        # These endpoints must work for the setup form to function
        # =====================================================
        
        if self._is_company_setup_path(request.path):
            logger.info(f"[REG COMPLETION] ✅✅✅ COMPANY SETUP - BYPASSING: {request.path} [{request.method}]")
            return self.get_response(request)
        
        # =====================================================
        # Standard exemptions
        # =====================================================
        exempt_paths = [
            '/static/',
            '/media/',
            '/admin/',
        ]
        
        if ADMIN_PATH_REGEX.match(request.path) or any(request.path.startswith(path) for path in exempt_paths):
            logger.debug(f"[REG COMPLETION] ✅ EXEMPT PATH")
            return self.get_response(request)
        
        # =====================================================
        # POST requests - Generally allow through
        # (Step order only matters for GET requests to view pages)
        # =====================================================
        if request.method == 'POST':
            logger.debug(f"[REG COMPLETION] ✅ POST request, allowing")
            return self.get_response(request)
        
        # =====================================================
        # Only check step order for setup GET pages
        # =====================================================
        if not self._is_company_setup_path(request.path):
            return self.get_response(request)
        
        # Skip main setup page
        if request.path == '/company/setup/' or re.match(r'^/[A-Z0-9-]+/company/setup/$', request.path):
            logger.debug(f"[REG COMPLETION] ✅ Main setup page")
            return self.get_response(request)
        
        logger.debug(f"[REG COMPLETION] Checking step order")
        
        # =====================================================
        # Users in setup flow - Allow
        # =====================================================
        setup_company_id = request.session.get('setup_company_id')
        company_id = request.session.get('company_id')
        
        if setup_company_id or company_id:
            logger.debug(f"[REG COMPLETION] ✅ User in setup flow")
            return self.get_response(request)
        
        # =====================================================
        # Superuser - Allow
        # =====================================================
        if request.user.is_authenticated and request.user.is_superuser:
            logger.debug(f"[REG COMPLETION] ✅ Superuser")
            return self.get_response(request)
        
        # =====================================================
        # Check step completion for GET requests
        # =====================================================
        registration_step = request.session.get('registration_step', 0)
        
        try:
            current_view = resolve(request.path).url_name
            logger.debug(f"[REG COMPLETION] View: {current_view}, Step: {registration_step}")
            
            if current_view == 'register_license_activation':
                if not (setup_company_id or company_id) or registration_step < 1:
                    logger.info(f"[REG COMPLETION] ⚠️ Step 2 requires step 1")
                    return redirect_with_company('company_registration')
            
            elif current_view == 'complete_registration':
                if not (setup_company_id or company_id) or registration_step < 2:
                    logger.info(f"[REG COMPLETION] ⚠️ Step 3 requires step 2")
                    return redirect_with_company('company_registration')
        
        except Exception as e:
            logger.error(f"[REG COMPLETION] Error: {e}")
            pass
        
        logger.debug(f"[REG COMPLETION] ✅ Allowing request")
        return self.get_response(request)
    
    def _is_company_setup_path(self, path):
        """
        Check if path is a company setup path.
        Same logic as RegistrationFlowMiddleware.
        
        Returns:
            bool: True if path is a company setup path
        """
        # List of all company setup endpoints
        setup_paths = [
            '/company/setup/',
            '/company/setup/company-info/',
            '/company/setup/license-activation/',
            '/company/setup/complete/',
            '/company/setup/status/',
        ]
        
        # Check direct path match
        if any(path.startswith(setup_path) for setup_path in setup_paths):
            return True
        
        # Check company_code prefixed path match
        if re.match(r'^/[A-Z0-9-]+/company/setup/', path):
            return True
        
        return False
