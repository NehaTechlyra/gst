"""
CENTRAL REDIRECT UTILITY - Auto-handles company_code in ALL views
BULLETPROOF VERSION - Works everywhere automatically

Instead of manually passing company_code to every redirect, use these helpers:
    redirect_with_company(request, 'view_name')
    redirect_with_company(request, 'view_name', pk=123)
    
This automatically extracts company_code from the request and adds it to the redirect.
"""

from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
import logging
import inspect
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def get_company_code(request):
    """
    Extract company_code from request.
    
    Tries multiple sources in priority order:
    1. request.company_code (set by CompanyCodeMiddleware)
    2. request.session.get('company_code')
    3. request.resolver_match.kwargs.get('company_code')
    
    Returns: company_code string or None
    """
    # First try: direct attribute (set by middleware)
    if hasattr(request, 'company_code') and request.company_code:
        return request.company_code
    
    # Second try: session
    if hasattr(request, 'session'):
        company_code = request.session.get('company_code')
        if company_code:
            return company_code
    
    # Third try: URL kwargs (from resolver_match)
    if hasattr(request, 'resolver_match') and request.resolver_match:
        company_code = request.resolver_match.kwargs.get('company_code')
        if company_code:
            return company_code
    
    return None


def redirect_with_company(request, view_name=None, *args, **kwargs):
    """
    Redirect to a view, automatically adding company_code.
    
    USAGE EXAMPLES:
    
    1. Simple redirect (no args):
        return redirect_with_company(request, 'brand_list')
        
    2. Redirect with ID:
        return redirect_with_company(request, 'brand_detail', pk=brand.id)
        return redirect_with_company(request, 'brand_detail', pk=123)
        
    3. Redirect with multiple kwargs:
        return redirect_with_company(request, 'order_detail', pk=123, status='active')
        
    4. Works with positional args too:
        return redirect_with_company(request, 'employee_detail', 42)
    
    REPLACES THIS OLD CODE:
        return redirect_with_company('brand_list', company_code=company_code)
        
    WITH THIS:
        return redirect_with_company(request, 'brand_list')
    """
    # Support legacy calling convention:
    # - redirect_with_company(request, 'view_name', ...)
    # - redirect_with_company('view_name', ...)
    req = None
    if view_name is None:
        # Called like redirect_with_company('view_name', ...)
        view_name = request
        request = None
    else:
        # Standard: first arg is request
        req = request

    # If no request provided, try to find one in the caller stack (for legacy calls)
    def _find_request_in_stack():
        for frame_info in inspect.stack()[1:10]:
            frame = frame_info.frame
            try:
                local_request = frame.f_locals.get('request')
                if isinstance(local_request, HttpRequest):
                    return local_request
            except Exception:
                continue
        return None

    if req is None:
        req = _find_request_in_stack()

    url = get_company_redirect_url(req, view_name, *args, **kwargs)
    logger.debug(f"redirect_with_company: {view_name} -> {url}")
    return redirect(url)


def get_company_redirect_url(request, view_name, *args, **kwargs):
    """
    Same as redirect_with_company but returns just the URL string instead of HttpResponse.
    
    USAGE:
        url = get_company_redirect_url(request, 'brand_list')
        url = get_company_redirect_url(request, 'brand_detail', pk=123)
    """
    # Get company_code from request
    company_code = get_company_code(request)
    
    # Prepare kwargs copy so we can mutate
    final_kwargs = dict(kwargs)
    if company_code:
        final_kwargs['company_code'] = company_code

    url = None

    # Try reverse with args only when args are provided (avoid mixing args+kwargs)
    if args:
        try:
            url = reverse(view_name, args=args)
        except NoReverseMatch:
            url = None

    # If args failed or not provided, try kwargs (which may include company_code)
    if url is None:
        try:
            url = reverse(view_name, kwargs=final_kwargs)
        except NoReverseMatch:
            # Try without company_code if present
            if 'company_code' in final_kwargs:
                final_kwargs.pop('company_code')
                try:
                    url = reverse(view_name, kwargs=final_kwargs)
                except NoReverseMatch:
                    url = None

    # If still failing and we have args, retry args-only reverse to ensure we return something
    if url is None and args:
        try:
            url = reverse(view_name, args=args)
        except NoReverseMatch:
            url = None

    # Prefix company_code manually if the url came from args-only reverse
    if url and company_code and f'/{company_code}/' not in url:
        if not url.startswith('/'):
            url = f'/{company_code}/{url.lstrip("/")}'
        elif not url.startswith(f'/{company_code}/'):
            url = f'/{company_code}{url}'

    if url:
        return url

    logger.error(f"Failed to reverse '{view_name}'")
    return view_name  # Return view name as fallback


def url_with_company(request, view_name, *args, **kwargs):
    """
    Alias for get_company_redirect_url for consistency.
    Use this in templates or views when you need just the URL string.
    """
    return get_company_redirect_url(request, view_name, *args, **kwargs)


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Alias for backward compatibility
redirect_to = redirect_with_company
