# by adarsh - role based permission for System Settings (Period Lock)
from user.utils import has_permission

# Aliases used in RolePermission.module names
_PERIOD_LOCK_ALIASES = ['System settings Period Lock', 'System settings Period lock']

# Other settings (Prefixes / Backup / Misc)
_OTHER_ALIASES = [
    'System settings Other',
    'System settings Other Settings',
]

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


# Period Lock helpers - by adarsh
def can_view_period_lock(user):
    return _any_alias_has_perm(user, _PERIOD_LOCK_ALIASES, 'View')


def can_create_period_lock(user):
    return _any_alias_has_perm(user, _PERIOD_LOCK_ALIASES, 'Create')


def can_edit_period_lock(user):
    return _any_alias_has_perm(user, _PERIOD_LOCK_ALIASES, 'Edit')


def can_delete_period_lock(user):
    return _any_alias_has_perm(user, _PERIOD_LOCK_ALIASES, 'Delete')

# Other settings helpers
def can_view_other(user):
    return _any_alias_has_perm(user, _OTHER_ALIASES, 'View')


def can_create_other(user):
    return _any_alias_has_perm(user, _OTHER_ALIASES, 'Create')


def can_edit_other(user):
    return _any_alias_has_perm(user, _OTHER_ALIASES, 'Edit')


def can_delete_other(user):
    return _any_alias_has_perm(user, _OTHER_ALIASES, 'Delete')
