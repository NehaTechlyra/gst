# from django.db.models.signals import post_save, pre_delete, pre_save
# from django.dispatch import receiver
# from django.contrib.contenttypes.models import ContentType
# from .models import ActivityLog
# from .utils import log_activity, get_model_changes
# from django.core.cache import cache

# # List of models to track (add your models here)
# TRACKED_MODELS = [
#     'SalesQuotation',
#     'SalesOrder',
#     'SalesInvoice',
#     'Customer',
#     'Item',
#     'PurchaseOrder',
#     'Vendor',
#     'User',
#     'Expense',
#     'payment',
#     # Add more models as needed
# ]

# def should_track_model(instance):
#     """Check if the model should be tracked."""
#     model_name = instance.__class__.__name__
#     return model_name in TRACKED_MODELS

# @receiver(pre_save)
# def capture_old_values(sender, instance, **kwargs):
#     """Capture old values before update."""
#     if not should_track_model(instance):
#         return
    
#     if instance.pk:  # Only for updates
#         try:
#             old_instance = sender.objects.get(pk=instance.pk)
#             # Store in cache temporarily
#             cache_key = f'old_instance_{sender.__name__}_{instance.pk}'
#             cache.set(cache_key, old_instance, 60)  # 60 seconds timeout
#         except sender.DoesNotExist:
#             pass

# @receiver(post_save)
# def log_model_save(sender, instance, created, **kwargs):
#     """Log CREATE and UPDATE operations."""
#     if not should_track_model(instance):
#         return
    
#     # Skip if this is an ActivityLog itself
#     if isinstance(instance, ActivityLog):
#         return
    
#     # Get user from instance or current request
#     user = None
#     if hasattr(instance, 'created_by'):
#         user = instance.created_by
#     elif hasattr(instance, 'updated_by'):
#         user = instance.updated_by
    
#     if created:
#         # Log CREATE
#         log_activity(
#             user=user,
#             action='CREATE',
#             content_object=instance,
#             description=f"Created {instance.__class__.__name__}: {str(instance)}",
#             new_values=get_model_dict(instance),
#         )
#     else:
#         # Log UPDATE
#         cache_key = f'old_instance_{sender.__name__}_{instance.pk}'
#         old_instance = cache.get(cache_key)
        
#         if old_instance:
#             changes = get_model_changes(old_instance, instance)
            
#             if changes:  # Only log if there are actual changes
#                 log_activity(
#                     user=user,
#                     action='UPDATE',
#                     content_object=instance,
#                     description=f"Updated {instance.__class__.__name__}: {str(instance)}",
#                     changes=changes,
#                     old_values=get_model_dict(old_instance),
#                     new_values=get_model_dict(instance),
#                 )
            
#             # Clean up cache
#             cache.delete(cache_key)

# @receiver(pre_delete)
# def log_model_delete(sender, instance, **kwargs):
#     """Log DELETE operations."""
#     if not should_track_model(instance):
#         return
    
#     # Skip if this is an ActivityLog itself
#     if isinstance(instance, ActivityLog):
#         return
    
#     # Get user
#     user = None
#     if hasattr(instance, 'updated_by'):
#         user = instance.updated_by
#     elif hasattr(instance, 'created_by'):
#         user = instance.created_by
    
#     log_activity(
#         user=user,
#         action='DELETE',
#         content_object=instance,
#         description=f"Deleted {instance.__class__.__name__}: {str(instance)}",
#         old_values=get_model_dict(instance),
#     )

# def get_model_dict(instance):
#     """Convert model instance to dictionary."""
#     data = {}
#     for field in instance._meta.fields:
#         value = getattr(instance, field.name, None)
#         if value is not None:
#             data[field.name] = str(value)
#     return data



#by sisira
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog
from .utils import log_activity, get_model_changes
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# List of models to track (add your models here)
TRACKED_MODELS = [
    'SalesQuotation',
    'SalesOrder',
    'SalesInvoice',
    'Customer',
    'Item',
    'PurchaseOrder',
    'Vendor',
    'User',
    'Expense',
    'payment',
    # Add more models as needed
]

def should_track_model(instance):
    """Check if the model should be tracked."""
    model_name = instance.__class__.__name__
    return model_name in TRACKED_MODELS

@receiver(pre_save)
def capture_old_values(sender, instance, **kwargs):
    """Capture old values before update."""
    if not should_track_model(instance):
        return
    
    if instance.pk:  # Only for updates
        try:
            # ✅ FIX: Use the same database as the instance
            db_alias = instance._state.db or 'default'
            old_instance = sender.objects.using(db_alias).get(pk=instance.pk)
            
            # Store in cache temporarily
            cache_key = f'old_instance_{sender.__name__}_{instance.pk}_{db_alias}'
            cache.set(cache_key, old_instance, 60)  # 60 seconds timeout
            
            logger.debug(f"📝 [SIGNAL] Captured old values for {sender.__name__} from {db_alias}")
            
        except sender.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"⚠️ [SIGNAL] Could not capture old values: {e}")

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log CREATE and UPDATE operations."""
    if not should_track_model(instance):
        return
    
    # Skip if this is an ActivityLog itself
    if isinstance(instance, ActivityLog):
        return
    
    try:
        # Get user from instance or current request
        user = None
        request = None
        
        # Try to get user from various sources
        if hasattr(instance, 'created_by') and instance.created_by:
            user = instance.created_by
        elif hasattr(instance, 'updated_by') and instance.updated_by:
            user = instance.updated_by
        elif hasattr(instance, '_current_user'):
            user = instance._current_user
        
        # Get request if available (for IP and user agent)
        if hasattr(instance, '_current_request'):
            request = instance._current_request
        
        # Skip if no user (can't log without user)
        if not user:
            logger.debug(f"⚠️ [SIGNAL] Skipping activity log for {sender.__name__} - no user found")
            return
        
        # ✅ FIX: Get database from instance
        db_alias = instance._state.db or 'default'
        
        if created:
            # Log CREATE
            log_activity(
                user=user,
                action='CREATE',
                content_object=instance,
                description=f"Created {instance.__class__.__name__}: {str(instance)}",
                new_values=get_model_dict(instance),
                request=request,
            )
            logger.debug(f"✅ [SIGNAL] Logged CREATE for {sender.__name__} in {db_alias}")
            
        else:
            # Log UPDATE
            cache_key = f'old_instance_{sender.__name__}_{instance.pk}_{db_alias}'
            old_instance = cache.get(cache_key)
            
            if old_instance:
                changes = get_model_changes(old_instance, instance)
                
                if changes:  # Only log if there are actual changes
                    log_activity(
                        user=user,
                        action='UPDATE',
                        content_object=instance,
                        description=f"Updated {instance.__class__.__name__}: {str(instance)}",
                        changes=changes,
                        old_values=get_model_dict(old_instance),
                        new_values=get_model_dict(instance),
                        request=request,
                    )
                    logger.debug(f"✅ [SIGNAL] Logged UPDATE for {sender.__name__} in {db_alias}")
                
                # Clean up cache
                cache.delete(cache_key)
            else:
                logger.debug(f"⚠️ [SIGNAL] No old instance found in cache for {sender.__name__}")
                
    except Exception as e:
        logger.error(f"❌ [SIGNAL] Error logging save for {sender.__name__}: {e}", exc_info=True)

@receiver(pre_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log DELETE operations."""
    if not should_track_model(instance):
        return
    
    # Skip if this is an ActivityLog itself
    if isinstance(instance, ActivityLog):
        return
    
    try:
        # Get user
        user = None
        request = None
        
        if hasattr(instance, 'updated_by') and instance.updated_by:
            user = instance.updated_by
        elif hasattr(instance, 'created_by') and instance.created_by:
            user = instance.created_by
        elif hasattr(instance, '_current_user'):
            user = instance._current_user
        
        # Get request if available
        if hasattr(instance, '_current_request'):
            request = instance._current_request
        
        # Skip if no user
        if not user:
            logger.debug(f"⚠️ [SIGNAL] Skipping delete log for {sender.__name__} - no user found")
            return
        
        # ✅ FIX: Get database from instance
        db_alias = instance._state.db or 'default'
        
        log_activity(
            user=user,
            action='DELETE',
            content_object=instance,
            description=f"Deleted {instance.__class__.__name__}: {str(instance)}",
            old_values=get_model_dict(instance),
            request=request,
        )
        
        logger.debug(f"✅ [SIGNAL] Logged DELETE for {sender.__name__} in {db_alias}")
        
    except Exception as e:
        logger.error(f"❌ [SIGNAL] Error logging delete for {sender.__name__}: {e}", exc_info=True)

def get_model_dict(instance):
    """Convert model instance to dictionary."""
    data = {}
    try:
        for field in instance._meta.fields:
            value = getattr(instance, field.name, None)
            if value is not None:
                data[field.name] = str(value)
    except Exception as e:
        logger.warning(f"⚠️ [SIGNAL] Error converting model to dict: {e}")
    return data