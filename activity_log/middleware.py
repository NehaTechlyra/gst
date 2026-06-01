# from .models import ActivityLog
# from .utils import get_client_ip, get_user_agent

# class ActivityLogMiddleware:
#     """
#     Middleware to automatically capture request context for activity logging.
#     """
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         # Store request data for use in signals
#         request._activity_log_ip = get_client_ip(request)
#         request._activity_log_user_agent = get_user_agent(request)
        
#         response = self.get_response(request)
#         return response


#by sisira
from .models import ActivityLog
from .utils import get_client_ip, get_user_agent
import logging

logger = logging.getLogger(__name__)

class ActivityLogMiddleware:
    """
    Middleware to automatically capture request context for activity logging.
    Stores IP address, user agent, and company database for use in signals and utils.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Capture IP address and user agent
            request._activity_log_ip = get_client_ip(request)
            request._activity_log_user_agent = get_user_agent(request)
            
            # ✅ CRITICAL: Capture company database for activity logging
            # This is set by CompanyDBMiddleware which runs before this middleware
            request._activity_log_company_db = getattr(request, 'company_db', 'default')
            
            logger.debug(
                f"📝 [ACTIVITY MIDDLEWARE] Captured context - "
                f"IP: {request._activity_log_ip}, "
                f"DB: {request._activity_log_company_db}, "
                f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
            )
            
        except Exception as e:
            logger.warning(f"⚠️ [ACTIVITY MIDDLEWARE] Could not capture activity context: {e}")
            # Set defaults to prevent errors downstream
            request._activity_log_ip = ''
            request._activity_log_user_agent = ''
            request._activity_log_company_db = 'default'
        
        response = self.get_response(request)
        return response