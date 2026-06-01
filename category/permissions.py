# by copilot - role based permission for Masters Category
from user.utils import has_permission

_CATEGORY_ALIASES = ['Masters Category', 'Category']


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


def can_view_categories(user):
    return _any_alias_has_perm(user, _CATEGORY_ALIASES, 'View')


def can_create_categories(user):
    return _any_alias_has_perm(user, _CATEGORY_ALIASES, 'Create')


def can_edit_categories(user):
    return _any_alias_has_perm(user, _CATEGORY_ALIASES, 'Edit')


def can_delete_categories(user):
    return _any_alias_has_perm(user, _CATEGORY_ALIASES, 'Delete')
