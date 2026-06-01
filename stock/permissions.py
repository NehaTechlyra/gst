from user.utils import has_permission

# Aliases used in RolePermission.module names
_STOCK_ALIASES = ['Masters Stock', 'Stock', 'stock']


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


# Masters Stock helpers
def can_view_stock(user):
    return _any_alias_has_perm(user, _STOCK_ALIASES, 'View')


def can_create_stock(user):
    return _any_alias_has_perm(user, _STOCK_ALIASES, 'Create')


def can_edit_stock(user):
    return _any_alias_has_perm(user, _STOCK_ALIASES, 'Edit')


def can_delete_stock(user):
    return _any_alias_has_perm(user, _STOCK_ALIASES, 'Delete')
