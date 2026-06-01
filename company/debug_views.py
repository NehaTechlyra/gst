from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from company.models import Company, LicenseKey


@login_required
def debug_middleware_status(request):
    """
    Debug view to check middleware status
    Access: /debug/middleware/
    """
    
    # Check company status
    company_exists = Company.objects.exists()
    company = Company.objects.first() if company_exists else None
    
    # Check license status
    license_obj = None
    if company:
        try:
            license_obj = LicenseKey.objects.get(company=company)
        except LicenseKey.DoesNotExist:
            pass
    
    # Session data
    session_data = {
        'company_id': request.session.get('company_id'),
        'login_username': request.session.get('login_username'),
        'usr_roleid': request.session.get('usr_roleid'),
        'registration_step': request.session.get('registration_step'),
        'registration_complete': request.session.get('registration_complete'),
        'license_activated': request.session.get('license_activated'),
    }
    
    # User data
    user_data = {
        'username': request.user.username,
        'is_authenticated': request.user.is_authenticated,
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
    }
    
    # Company data
    company_data = None
    if company:
        company_data = {
            'id': company.id,
            'name': company.name,
            'email': company.email,
        }
    
    # License data
    license_data = None
    if license_obj:
        license_data = {
            'license_key': license_obj.license_key,
            'is_active': license_obj.is_active,
            'is_expired': license_obj.is_expired(),
            'expiry_date': str(license_obj.expiry_date) if license_obj.expiry_date else None,
            'days_remaining': license_obj.days_remaining(),
        }
    
    # Middleware flow analysis
    middleware_analysis = {
        'should_redirect_to_login': not request.user.is_authenticated,
        'should_redirect_to_registration': request.user.is_authenticated and not company_exists,
        'should_check_license': request.user.is_authenticated and company_exists,
        'registration_path_exempt': request.path.startswith('/setup/'),
    }
    
    return JsonResponse({
        'success': True,
        'user': user_data,
        'session': session_data,
        'company': company_data,
        'license': license_data,
        'middleware_analysis': middleware_analysis,
        'current_path': request.path,
        'next_action': _get_next_action(request, company_exists, license_obj),
    }, json_dumps_params={'indent': 2})


def _get_next_action(request, company_exists, license_obj):
    """Determine what should happen next"""
    
    if not request.user.is_authenticated:
        return "Redirect to login"
    
    if request.user.is_superuser:
        return "Superuser - bypass all checks"
    
    if not company_exists:
        return "Redirect to company registration"
    
    if not license_obj:
        return "Redirect to license_required page"
    
    if license_obj.is_expired():
        return "Redirect to license_expired page"
    
    return "Allow access to dashboard"


# ========================================
# ADD TO urls.py TEMPORARILY
# ========================================
# from company.debug_views import debug_middleware_status
# 
# urlpatterns = [
#     # ... your other URLs ...
#     path('debug/middleware/', debug_middleware_status, name='debug_middleware'),
# ]