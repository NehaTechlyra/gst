# from .models import User, RolePermission
# import logging

# logger = logging.getLogger(__name__)


# def _get_app_user_from_auth(user):
#     """Try to map Django auth user to app's `user.User` record.
#     Strategy: match username -> usr_name. Returns None if not found.
#     """
#     if not user or not getattr(user, 'is_authenticated', False):
#         return None
#     try:
#         # Primary mapping: username -> usr_name
#         app_user = User.objects.filter(usr_name=user.username).first()
#         if app_user:
#             return app_user
#         # Fallback mapping: email -> usr_mail (some installations use email as username)
#         user_email = getattr(user, 'email', None)
#         if user_email:
#             app_user = User.objects.filter(usr_mail__iexact=user_email).first()
#             if app_user:
#                 return app_user
#         return None
#     except Exception:
#         return None


# def has_permission(user, module_name, permission_type):
#     """
#     Check if user has a specific permission for a module.
    
#     CRITICAL FIX: 
#     1. Full Access should grant ALL permissions including View
#     2. Support partial module name matching (e.g., "Sales" matches "Sales Invoice", "Sales Orders", etc.)
#     """
#     if not user or not user.is_authenticated:
#         return False
    
#     # Superusers bypass all permission checks
#     if getattr(user, 'is_superuser', False):
#         return True
    
#     try:
#         from user.models import User, RolePermission
        
#         # Get custom user from master DB
#         custom_user = User.objects.using('default').select_related(
#             'usr_roleid__company'
#         ).filter(usr_name=user.username).first()
        
#         if not custom_user or not custom_user.usr_roleid:
#             logger.warning(f"has_permission: No custom user or role found for {user.username}")
#             return False
        
#         role = custom_user.usr_roleid
#         company = role.company
        
#         if not company or not company.db_name:
#             logger.warning(f"has_permission: No company or db_name for user {user.username}")
#             return False
        
#         # ✅ CRITICAL FIX: Check for BOTH exact match AND partial match (icontains)
#         # First try exact match (case-insensitive)
#         perms = RolePermission.objects.using(company.db_name).filter(
#             role=role,
#             module__name__iexact=module_name,
#             allowed=1
#         ).select_related('permission_type')
        
#         for perm in perms:
#             perm_name = perm.permission_type.name
            
#             # ✅ If user has Full Access, grant ALL permissions
#             if perm_name == 'Full Access':
#                 logger.debug(f"✅ has_permission: {user.username} has Full Access to {module_name}")
#                 return True
            
#             # Otherwise check for specific permission
#             if perm_name == permission_type:
#                 logger.debug(f"✅ has_permission: {user.username} has {permission_type} for {module_name}")
#                 return True
        
#         # ✅ If no exact match, try partial match using icontains
#         # This handles cases like module_name="Sales" matching "Sales Invoice", "Sales Orders", etc.
#         perms_partial = RolePermission.objects.using(company.db_name).filter(
#             role=role,
#             module__name__icontains=module_name,
#             allowed=1
#         ).select_related('permission_type')
        
#         for perm in perms_partial:
#             perm_name = perm.permission_type.name
            
#             # ✅ If user has Full Access, grant ALL permissions
#             if perm_name == 'Full Access':
#                 logger.debug(f"✅ has_permission (partial): {user.username} has Full Access to {perm.module.name} (matches {module_name})")
#                 return True
            
#             # Otherwise check for specific permission
#             if perm_name == permission_type:
#                 logger.debug(f"✅ has_permission (partial): {user.username} has {permission_type} for {perm.module.name} (matches {module_name})")
#                 return True
        
#         logger.debug(f"❌ has_permission: {user.username} does NOT have {permission_type} for {module_name}")
#         return False
        
#     except Exception as e:
#         logger.error(f"has_permission error: {e}", exc_info=True)
#         return False




from .models import User, RolePermission
import logging

logger = logging.getLogger(__name__)


def _get_app_user_from_auth(user):
    """Try to map Django auth user to app's `user.User` record.
    Strategy: match username -> usr_name. Returns None if not found.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        # Primary mapping: username -> usr_name
        app_user = User.objects.filter(usr_name=user.username).first()
        if app_user:
            return app_user
        # Fallback mapping: email -> usr_mail (some installations use email as username)
        user_email = getattr(user, 'email', None)
        if user_email:
            app_user = User.objects.filter(usr_mail__iexact=user_email).first()
            if app_user:
                return app_user
        return None
    except Exception:
        return None


def is_app_admin_user(user):
    """Return True when the linked app user record is marked as an admin."""
    try:
        app_user = _get_app_user_from_auth(user)
        return bool(app_user and getattr(app_user, 'is_admin', False))
    except Exception:
        return False


def is_app_role_admin(user):
    """Return True when the linked app user record has the Admin role."""
    try:
        app_user = _get_app_user_from_auth(user)
        if not app_user or not getattr(app_user, 'usr_roleid', None):
            return False
        return getattr(app_user.usr_roleid, 'role_name', '').strip().lower() == 'admin'
    except Exception:
        return False


def has_permission(user, module_name, permission_type):
    """
    Check if user has a specific permission for a module.
    
    CRITICAL FIXES: 
    1. Full Access should grant ALL permissions including View
    2. Support partial module name matching (e.g., "Sales" matches "Sales Invoice", "Sales Orders", etc.)
    3. Query company database for role, not master database (role IDs can differ between databases)
    4. ✅ NEW: Trial users have unrestricted access to all modules and permissions
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superusers bypass all permission checks
    if getattr(user, 'is_superuser', False):
        return True
    
    try:
        from user.models import User, RolePermission
        
        # ✅ CRITICAL FIX: First get company info from master DB
        master_user = User.objects.using('default').select_related(
            'usr_roleid__company'
        ).filter(usr_name=user.username).first()
        
        if not master_user or not master_user.usr_roleid:
            logger.warning(f"has_permission: No custom user or role found for {user.username} in master DB")
            return False
        
        company = master_user.usr_roleid.company
        
        if not company or not company.db_name:
            logger.warning(f"has_permission: No company or db_name for user {user.username}")
            return False
        
        company_db = company.db_name
        
        # [OK] NEW: Trial users get full access to all modules and permissions
        # if getattr(company, 'trial_active', False):
        #     logger.info(f"[OK] has_permission: {user.username} is in TRIAL mode - granting all permissions for {module_name}.{permission_type}")
        #     return True
        
        # ✅ CRITICAL FIX: Now get the user and role FROM THE COMPANY DATABASE
        # The role ID in company DB may differ from master DB!
        custom_user = User.objects.using(company_db).select_related(
            'usr_roleid'
        ).filter(usr_name=user.username).first()
        
        if not custom_user or not custom_user.usr_roleid:
            logger.warning(f"has_permission: No user or role found in {company_db} for {user.username}")
            return False
        
        role = custom_user.usr_roleid  # This is the role from company DB with correct ID
        
        logger.debug(f"has_permission: Checking {user.username} (role ID {role.id} in {company_db}) for {module_name}.{permission_type}")
        
        # ✅ Check for BOTH exact match AND partial match (icontains)
        # First try exact match (case-insensitive)
        perms = RolePermission.objects.using(company_db).filter(
            role=role,
            module__name__iexact=module_name,
            allowed=1
        ).select_related('permission_type')
        
        for perm in perms:
            perm_name = perm.permission_type.name
            
            # [OK] If user has Full Access, grant ALL permissions
            if perm_name == 'Full Access':
                logger.debug(f"[OK] has_permission: {user.username} has Full Access to {module_name}")
                return True
            
            # Otherwise check for specific permission
            if perm_name == permission_type:
                logger.debug(f"[OK] has_permission: {user.username} has {permission_type} for {module_name}")
                return True
        
        # For top-level "Sales", require exact match only.
        # This prevents users with a single submodule (e.g. "Sales Quotation")
        # from being treated as having broad "Sales" permission.
        if (module_name or '').strip().lower() == 'sales':
            logger.debug(f"has_permission: exact-only module '{module_name}' not granted for {user.username}")
            return False

        # [OK] If no exact match, try partial match using icontains.
        # Useful for minor naming differences (e.g., singular/plural variants).
        perms_partial = RolePermission.objects.using(company_db).filter(
            role=role,
            module__name__icontains=module_name,
            allowed=1
        ).select_related('permission_type')
        
        for perm in perms_partial:
            # Safeguard: prevent "Sales Eway Bill" from matching "Purchase" or generic "Bill" requests
            if 'eway' in (perm.module.name or '').lower() and 'eway' not in (module_name or '').lower():
                continue

            perm_name = perm.permission_type.name
            
            # [OK] If user has Full Access, grant ALL permissions
            if perm_name == 'Full Access':
                logger.debug(f"[OK] has_permission (partial): {user.username} has Full Access to {perm.module.name} (matches {module_name})")
                return True
            
            # Otherwise check for specific permission
            if perm_name == permission_type:
                logger.debug(f"[OK] has_permission (partial): {user.username} has {permission_type} for {perm.module.name} (matches {module_name})")
                return True
        
        logger.debug(f"[ERROR] has_permission: {user.username} does NOT have {permission_type} for {module_name}")
        return False
        
    except Exception as e:
        logger.error(f"has_permission error: {e}", exc_info=True)
        return False
