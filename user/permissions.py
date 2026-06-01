from .utils import has_permission

# Aliases used in RolePermission.module names
_USER_ROLES_ALIASES = ['Masters User Roles', 'User Roles']
_USERS_ALIASES = ['Masters Users', 'Users']


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


# Masters User Roles helpers
def can_view_user_roles(user):
    return _any_alias_has_perm(user, _USER_ROLES_ALIASES, 'View')


def can_create_user_roles(user):
    return _any_alias_has_perm(user, _USER_ROLES_ALIASES, 'Create')


def can_edit_user_roles(user):
    return _any_alias_has_perm(user, _USER_ROLES_ALIASES, 'Edit')


def can_delete_user_roles(user):
    return _any_alias_has_perm(user, _USER_ROLES_ALIASES, 'Delete')


# Masters Users helpers
def can_view_users(user):
    return _any_alias_has_perm(user, _USERS_ALIASES, 'View')


def can_create_users(user):
    return _any_alias_has_perm(user, _USERS_ALIASES, 'Create')


def can_edit_users(user):
    return _any_alias_has_perm(user, _USERS_ALIASES, 'Edit')


def can_delete_users(user):
    return _any_alias_has_perm(user, _USERS_ALIASES, 'Delete')
