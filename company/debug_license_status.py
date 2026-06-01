"""
Debug view to check license and trial status across all databases
Access via: /debug-license-status/?company_id=2
"""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import date
import logging
import json

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@csrf_exempt
def debug_license_status(request):
    """
    Returns detailed license and trial status for debugging
    """
    company_id = request.GET.get('company_id')
    
    if not company_id:
        return JsonResponse({
            'error': 'Please provide company_id parameter',
            'example': '/debug-license-status/?company_id=2'
        }, status=400)
    
    try:
        from company.models import Company
        from company_settings.models import LicenseKey
        
        # Get company from master DB
        company = Company.objects.using('default').get(id=company_id)
        company_db = company.db_name or 'default'
        
        # Get company from company DB
        company_in_db = Company.objects.using(company_db).get(id=company_id)
        
        # Get license from company DB (where it actually matters)
        try:
            license_obj = LicenseKey.objects.using(company_db).get(company_id=company_id)
        except LicenseKey.DoesNotExist:
            license_obj = None
        
        today = date.today()
        now = timezone.now()
        
        return JsonResponse({
            'company': {
                'id': company.id,
                'name': company.name,
                'db_name': company_db,
                'setup_complete': company.setup_complete,
                'first_login_completed': company.first_login_completed,
            },
            'license': {
                'exists': license_obj is not None,
                'id': license_obj.id if license_obj else None,
                'license_key': license_obj.license_key[:15] + '...' if license_obj else None,
                'is_active': license_obj.is_active if license_obj else None,
                'is_license_expired': license_obj.is_license_expired if license_obj else None,
                'is_expired_method': license_obj.is_expired() if license_obj and hasattr(license_obj, 'is_expired') else None,
                'issue_date': license_obj.issue_date.isoformat() if license_obj and license_obj.issue_date else None,
                'expiry_date': license_obj.expiry_date.isoformat() if license_obj and license_obj.expiry_date else None,
                'days_until_expiry': (license_obj.expiry_date - today).days if license_obj and license_obj.expiry_date else None,
                'expiry_date_has_passed': today > license_obj.expiry_date if license_obj and license_obj.expiry_date else None,
                'max_users': license_obj.max_users if license_obj else None,
                'module_access': license_obj.module_access if license_obj else None,
                'activated_at': license_obj.activated_at.isoformat() if license_obj and license_obj.activated_at else None,
            },
            'trial': {
                'trial_active': company_in_db.trial_active if hasattr(company_in_db, 'trial_active') else False,
                'is_trial_expired': company_in_db.is_trial_expired if hasattr(company_in_db, 'is_trial_expired') else None,
                'trial_started_at': company_in_db.trial_started_at.isoformat() if hasattr(company_in_db, 'trial_started_at') and company_in_db.trial_started_at else None,
                'trial_expires_at': company_in_db.trial_expires_at.isoformat() if hasattr(company_in_db, 'trial_expires_at') and company_in_db.trial_expires_at else None,
                'days_until_trial_expires': company_in_db.days_until_trial_expires() if hasattr(company_in_db, 'days_until_trial_expires') else None,
            },
            'current_time': {
                'now': now.isoformat(),
                'today': today.isoformat(),
            },
            'middleware_logic': {
                'has_license': license_obj is not None and license_obj.is_active if license_obj else False,
                'license_is_valid': (
                    False if not license_obj else (
                        not license_obj.is_license_expired 
                        if hasattr(license_obj, 'is_license_expired') 
                        else (today <= license_obj.expiry_date if license_obj.expiry_date else False)
                    )
                ),
                'license_is_expired': (
                    True if not license_obj else (
                        license_obj.is_license_expired 
                        if hasattr(license_obj, 'is_license_expired') 
                        else (today > license_obj.expiry_date if license_obj.expiry_date else False)
                    )
                ),
                'trial_is_active': hasattr(company_in_db, 'trial_active') and company_in_db.trial_active,
                'trial_is_expired': hasattr(company_in_db, 'is_trial_expired') and company_in_db.is_trial_expired,
            },
            'expected_result': determine_expected_result(
                has_license=license_obj is not None and license_obj.is_active,
                is_expired=license_obj.is_license_expired if license_obj else True,
                trial_active=company_in_db.trial_active if hasattr(company_in_db, 'trial_active') else False,
                trial_expired=company_in_db.is_trial_expired if hasattr(company_in_db, 'is_trial_expired') else True,
            ),
        }, json_dumps_params={'indent': 2})
        
    except Company.DoesNotExist:
        return JsonResponse({
            'error': f'Company {company_id} not found'
        }, status=404)
    except Exception as e:
        logger.exception("Error in debug_license_status")
        return JsonResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status=500)


def determine_expected_result(has_license, is_expired, trial_active, trial_expired):
    """Predict what the middleware will do"""
    
    if has_license and not is_expired and (trial_active or True):  # If license valid, allow
        return '✅ ALLOW - License is valid'
    
    if has_license and is_expired:
        if trial_expired:
            return '❌ Show License Expired Page - License expired and trial ended'
        else:
            return '❌ Show Restricted Page - License expired (but trial may still be active)'
    
    if trial_active and not trial_expired:
        return '✅ ALLOW - Trial is active'
    
    if trial_expired:
        return '❌ Show Trial Expired Page - Trial has expired'
    
    return '❌ Show Blocked Page - No valid license or trial'
