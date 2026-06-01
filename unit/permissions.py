# by adarsh - role based permission for Masters Unit
from user.utils import has_permission

# Aliases used in RolePermission.module names
_UNIT_ALIASES = ['Masters Unit', 'Unit']


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


# Masters Unit helpers - by adarsh
def can_view_units(user):
    return _any_alias_has_perm(user, _UNIT_ALIASES, 'View')


def can_create_units(user):
    return _any_alias_has_perm(user, _UNIT_ALIASES, 'Create')


def can_edit_units(user):
    return _any_alias_has_perm(user, _UNIT_ALIASES, 'Edit')


def can_delete_units(user):
    return _any_alias_has_perm(user, _UNIT_ALIASES, 'Delete')
