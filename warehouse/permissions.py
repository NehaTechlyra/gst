from user.utils import has_permission

# Aliases used in RolePermission.module names
_WAREHOUSE_ALIASES = ['Masters Warehouse', 'Masters warehouse', 'Warehouse', 'warehouse']


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


# Masters Warehouse helpers
def can_view_warehouse(user):
    return _any_alias_has_perm(user, _WAREHOUSE_ALIASES, 'View')


def can_create_warehouse(user):
    return _any_alias_has_perm(user, _WAREHOUSE_ALIASES, 'Create')


def can_edit_warehouse(user):
    return _any_alias_has_perm(user, _WAREHOUSE_ALIASES, 'Edit')


def can_delete_warehouse(user):
    return _any_alias_has_perm(user, _WAREHOUSE_ALIASES, 'Delete')
