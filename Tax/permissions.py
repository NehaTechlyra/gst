from user.utils import has_permission

# Aliases used in RolePermission.module names
_TAX_ALIASES = ['Masters Taxes', 'Masters Tax', 'Taxes', 'Tax']


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


# Masters Taxes helpers
def can_view_taxes(user):
    return _any_alias_has_perm(user, _TAX_ALIASES, 'View')


def can_create_taxes(user):
    return _any_alias_has_perm(user, _TAX_ALIASES, 'Create')


def can_edit_taxes(user):
    return _any_alias_has_perm(user, _TAX_ALIASES, 'Edit')


def can_delete_taxes(user):
    return _any_alias_has_perm(user, _TAX_ALIASES, 'Delete')
