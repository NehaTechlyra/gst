from functools import wraps
from .utils import log_activity

def log_view_activity(action='VIEW', description=None):
    """
    Decorator to automatically log view activity.
    
    Usage:
        @log_view_activity(action='VIEW', description='Viewed quotation detail')
        def quotation_detail(request, pk):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Log the activity after successful view execution
            if hasattr(response, 'status_code') and response.status_code == 200:
                desc = description or f"Accessed {view_func.__name__}"
                log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    action=action,
                    description=desc,
                    request=request
                )
            
            return response
        return wrapper
    return decorator