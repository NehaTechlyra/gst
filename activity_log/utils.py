# from django.contrib.contenttypes.models import ContentType
# from .models import ActivityLog
# import json

# def get_client_ip(request):
#     """Get client IP address from request."""
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         ip = x_forwarded_for.split(',')[0]
#     else:
#         ip = request.META.get('REMOTE_ADDR')
#     return ip

# def get_user_agent(request):
#     """Get user agent from request."""
#     return request.META.get('HTTP_USER_AGENT', '')

# def log_activity(
#     user,
#     action,
#     content_object=None,
#     description='',
#     changes=None,
#     old_values=None,
#     new_values=None,
#     request=None,
#     related_object=None
# ):
#     """
#     Central function to log any activity.
    
#     Args:
#         user: User who performed the action
#         action: Action type (CREATE, UPDATE, DELETE, etc.)
#         content_object: The object that was affected
#         description: Human-readable description
#         changes: Dict of field changes
#         old_values: Dict of old values (for UPDATE)
#         new_values: Dict of new values (for UPDATE/CREATE)
#         request: HTTP request object (for IP and user agent)
#         related_object: Related object (e.g., customer for quotation)
#     """
#     try:
#         log_data = {
#             'user': user,
#             'action': action,
#             'description': description,
#             'changes': changes,
#             'old_values': old_values,
#             'new_values': new_values,
#         }
        
#         # Add content object info
#         if content_object:
#             log_data['content_type'] = ContentType.objects.get_for_model(content_object)
#             log_data['object_id'] = content_object.pk
#             log_data['object_repr'] = str(content_object)
#             log_data['model_name'] = content_object.__class__.__name__
        
#         # Add related object info
#         if related_object:
#             log_data['related_object_type'] = ContentType.objects.get_for_model(related_object)
#             log_data['related_object_id'] = related_object.pk
        
#         # Add request metadata
#         if request:
#             log_data['ip_address'] = get_client_ip(request)
#             log_data['user_agent'] = get_user_agent(request)
        
#         return ActivityLog.objects.create(**log_data)
#     except Exception as e:
#         # Don't let activity logging failures crash the application
#         import logging
#         logger = logging.getLogger(__name__)
#         logger.error(f"Failed to log activity: {e}", exc_info=True)
#         return None

# def get_model_changes(old_instance, new_instance, exclude_fields=None):
#     """
#     Compare two model instances and return changed fields.
    
#     Args:
#         old_instance: Original instance
#         new_instance: Updated instance
#         exclude_fields: List of fields to exclude from comparison
    
#     Returns:
#         dict: Dictionary of changes {field: {'old': old_val, 'new': new_val}}
#     """
#     if exclude_fields is None:
#         exclude_fields = ['id', 'created_at', 'updated_at', 'modified_at']
    
#     changes = {}
    
#     for field in new_instance._meta.fields:
#         if field.name in exclude_fields:
#             continue
        
#         old_value = getattr(old_instance, field.name, None)
#         new_value = getattr(new_instance, field.name, None)
        
#         # Convert to string for comparison
#         old_str = str(old_value) if old_value is not None else ''
#         new_str = str(new_value) if new_value is not None else ''
        
#         if old_str != new_str:
#             changes[field.name] = {
#                 'old': old_str,
#                 'new': new_str
#             }
    
#     return changes



#by sisira
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog
import json
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    """Get user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')

def log_activity(
    user,
    action,
    content_object=None,
    description='',
    changes=None,
    old_values=None,
    new_values=None,
    request=None,
    related_object=None
):
    """
    Central function to log any activity.
    
    Args:
        user: User who performed the action
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        content_object: The object that was affected
        description: Human-readable description
        changes: Dict of field changes
        old_values: Dict of old values (for UPDATE)
        new_values: Dict of new values (for UPDATE/CREATE)
        request: HTTP request object (for IP and user agent)
        related_object: Related object (e.g., customer for quotation)
    """
    try:
        # ✅ CRITICAL: Determine which database to use
        company_db = 'default'
        
        # Try to get company_db from request
        if request and hasattr(request, 'company_db'):
            company_db = request.company_db
            logger.debug(f"📝 [ACTIVITY] Using company_db from request: {company_db}")
        
        # Fallback: try to get from request._activity_log_company_db (set by middleware)
        elif request and hasattr(request, '_activity_log_company_db'):
            company_db = request._activity_log_company_db
            logger.debug(f"📝 [ACTIVITY] Using company_db from middleware: {company_db}")
        
        # If user has a role with company, use that
        elif hasattr(user, 'usr_roleid') and user.usr_roleid and hasattr(user.usr_roleid, 'company'):
            if user.usr_roleid.company and hasattr(user.usr_roleid.company, 'db_name'):
                company_db = user.usr_roleid.company.db_name
                logger.debug(f"📝 [ACTIVITY] Using company_db from user role: {company_db}")
        
        logger.info(f"📝 [ACTIVITY] Logging to database: {company_db}")
        
        log_data = {
            'user': user,
            'action': action,
            'description': description,
            'changes': changes,
            'old_values': old_values,
            'new_values': new_values,
        }
        
        # Add content object info
        if content_object:
            # ✅ Get ContentType from the same database
            try:
                log_data['content_type'] = ContentType.objects.db_manager(company_db).get_for_model(content_object)
                log_data['object_id'] = content_object.pk
                log_data['object_repr'] = str(content_object)
                log_data['model_name'] = content_object.__class__.__name__
            except Exception as ct_error:
                logger.warning(f"⚠️ [ACTIVITY] Could not get ContentType: {ct_error}")
                # Continue without content_type rather than failing
        
        # Add related object info
        if related_object:
            try:
                log_data['related_object_type'] = ContentType.objects.db_manager(company_db).get_for_model(related_object)
                log_data['related_object_id'] = related_object.pk
            except Exception as rel_error:
                logger.warning(f"⚠️ [ACTIVITY] Could not get related ContentType: {rel_error}")
        
        # Add request metadata
        if request:
            # Use middleware-captured values if available, otherwise capture now
            log_data['ip_address'] = getattr(request, '_activity_log_ip', None) or get_client_ip(request)
            log_data['user_agent'] = getattr(request, '_activity_log_user_agent', None) or get_user_agent(request)
        
        # ✅ CRITICAL: Create in company database, not master
        activity_log = ActivityLog.objects.using(company_db).create(**log_data)
        
        logger.info(f"✅ [ACTIVITY] Activity logged successfully in {company_db}: {action}")
        
        return activity_log
        
    except Exception as e:
        # Don't let activity logging failures crash the application
        logger.error(f"❌ [ACTIVITY] Failed to log activity: {e}", exc_info=True)
        return None

def get_model_changes(old_instance, new_instance, exclude_fields=None):
    """
    Compare two model instances and return changed fields.
    
    Args:
        old_instance: Original instance
        new_instance: Updated instance
        exclude_fields: List of fields to exclude from comparison
    
    Returns:
        dict: Dictionary of changes {field: {'old': old_val, 'new': new_val}}
    """
    if exclude_fields is None:
        exclude_fields = ['id', 'created_at', 'updated_at', 'modified_at']
    
    changes = {}
    
    try:
        for field in new_instance._meta.fields:
            if field.name in exclude_fields:
                continue
            
            old_value = getattr(old_instance, field.name, None)
            new_value = getattr(new_instance, field.name, None)
            
            # Convert to string for comparison
            old_str = str(old_value) if old_value is not None else ''
            new_str = str(new_value) if new_value is not None else ''
            
            if old_str != new_str:
                changes[field.name] = {
                    'old': old_str,
                    'new': new_str
                }
    except Exception as e:
        logger.error(f"❌ [ACTIVITY] Error getting model changes: {e}", exc_info=True)
    
    return changes



