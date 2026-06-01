from django.shortcuts import redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.urls import resolve
from .permissions import check_sales_module_access

class SalesPermissionMiddleware:
    """Middleware to check if user has permission to access Sales module pages."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Only check requests to sales URLs
            resolved = resolve(request.path)
            if resolved.app_name == 'sales':
                user = getattr(request, 'user', None)
                if not check_sales_module_access(user):
                    # Redirect to home or show permission denied
                    return redirect_with_company('home')  # or to a permission denied page
        except:
            pass  # Let other middleware handle any errors
            
        return self.get_response(request)