# by adarsh - role based permission for Masters Brand
from user.utils import has_permission

# Aliases used in RolePermission.module names
_BRAND_ALIASES = ['Masters Brand', 'Brand']


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


# Masters Brand helpers - by adarsh
def can_view_brands(user):
    return _any_alias_has_perm(user, _BRAND_ALIASES, 'View')


def can_create_brands(user):
    return _any_alias_has_perm(user, _BRAND_ALIASES, 'Create')


def can_edit_brands(user):
    return _any_alias_has_perm(user, _BRAND_ALIASES, 'Edit')


def can_delete_brands(user):
    return _any_alias_has_perm(user, _BRAND_ALIASES, 'Delete')
