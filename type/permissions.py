# by copilot - role based permission for Masters Type
from user.utils import has_permission

_TYPE_ALIASES = ['Masters Type', 'Type']


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


def can_view_types(user):
    return _any_alias_has_perm(user, _TYPE_ALIASES, 'View')


def can_create_types(user):
    return _any_alias_has_perm(user, _TYPE_ALIASES, 'Create')


def can_edit_types(user):
    return _any_alias_has_perm(user, _TYPE_ALIASES, 'Edit')


def can_delete_types(user):
    return _any_alias_has_perm(user, _TYPE_ALIASES, 'Delete')
