# by adarsh - role based permission for SMS Configuration
from user.utils import has_permission

# Aliases used in RolePermission.module names
_SMS_CONFIG_ALIASES = ['System settings SMS Configuration', 'System settings SMS config']


def _any_alias_has_perm(user, aliases, perm='View'):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            continue
    return False


# SMS Configuration helpers - by adarsh
def can_view_sms_config(user):
    return _any_alias_has_perm(user, _SMS_CONFIG_ALIASES, 'View')


def can_create_sms_config(user):
    return _any_alias_has_perm(user, _SMS_CONFIG_ALIASES, 'Create')


def can_edit_sms_config(user):
    return _any_alias_has_perm(user, _SMS_CONFIG_ALIASES, 'Edit')


def can_delete_sms_config(user):
    return _any_alias_has_perm(user, _SMS_CONFIG_ALIASES, 'Delete')
