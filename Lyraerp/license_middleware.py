# Lyraerp/middleware/license_middleware.py
"""
Middleware to inject license information into every request
"""
import logging
from company.models import Company
from Lyraerp.utils.license_utils import parse_license_key, get_allowed_modules_from_license

logger = logging.getLogger(__name__)


class LicenseMiddleware:
    """
    Add license information to every request
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add license info to request before view processes it
        self.process_request(request)
        
        response = self.get_response(request)
        return response
    
    def process_request(self, request):
        """
        Inject license information into request object
        """
        # Default: no license restrictions
        request.license_info = {
            'is_valid': True,
            'is_expired': False,
            'allowed_modules': None,  # None = all modules
            'expiry_date': None,
            'max_users': 999,
            'license_type': 'development'
        }
        
        # Skip for unauthenticated users
        if not request.user.is_authenticated:
            return
        
        # Get company from session
        company_id = request.session.get('company_id')
        if not company_id:
            logger.debug("No company_id in session")
            return
        
        try:
            # Get company database
            company_db = request.session.get('company_db', 'default')
            
            # Fetch company
            company = Company.objects.using(company_db).get(id=company_id)
            
            # Check if company has a license
            if hasattr(company, 'license') and company.license:
                license_obj = company.license
                
                # Get is_license_expired flag (set by scheduled task at midnight)
                is_expired = license_obj.is_license_expired
                
                # Parse license key for module list
                license_data = parse_license_key(license_obj.license_key)
                
                request.license_info = {
                    'is_valid': not is_expired,  # is_valid = NOT is_license_expired
                    'is_expired': is_expired,
                    'allowed_modules': license_data.get('modules', None),
                    'expiry_date': license_obj.expiry_date,
                    'max_users': license_obj.max_users,
                    'license_type': license_data.get('license_type', 'standard'),
                    'company_name': company.name
                }
                
                logger.debug(
                    f"License loaded for {company.name}: "
                    f"is_expired={is_expired}, "
                    f"expiry_date={license_obj.expiry_date}, "
                    f"allowed_modules={request.license_info['allowed_modules']}"
                )
            else:
                logger.warning(f"No license for company {company.name}, allowing all modules")
                
        except Company.DoesNotExist:
            logger.warning(f"Company {company_id} not found")
        except Exception as e:
            logger.error(f"Error loading license: {e}", exc_info=True)


