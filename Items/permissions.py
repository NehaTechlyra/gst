from user.utils import has_permission

# Define permissions aliases - by adarsh
_ITEMS_ALIASES = ['Items', 'Masters Items', 'Sales Items', 'items', 'Item']  # Main items module for all access
_INVENTORY_ALIASES = ['Inventory', 'Stock Management']  # Inventory management access

# Combined aliases for checking overall items access
_ALL_ITEMS_ALIASES = _ITEMS_ALIASES + _INVENTORY_ALIASES


def _any_alias_has_perm(user, aliases, perm='View'):
    """Return True if user has `perm` on any module name in `aliases`."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    # Superusers always have access
    if getattr(user, 'is_superuser', False):
        return True
        
    # Regular users need explicit permissions
    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            # ignore and continue to next alias
            continue
    return False


def check_items_access(user, perm='View'):
    """Check if user has items access."""
    return _any_alias_has_perm(user, _ITEMS_ALIASES, perm=perm)


def check_inventory_access(user, perm='View'):
    """Check if user has inventory management access."""
    return check_items_access(user, perm) or _any_alias_has_perm(user, _INVENTORY_ALIASES, perm=perm)


# Convenience helpers for common permission checks used by views/templates
def can_view_items(user):
    return check_items_access(user, 'View')


def can_create_items(user):
    return check_items_access(user, 'Create')


def can_edit_items(user):
    return check_items_access(user, 'Edit')


def can_delete_items(user):
    return check_items_access(user, 'Delete')


def can_view_inventory(user):
    return check_inventory_access(user, 'View')


def can_manage_inventory(user):
    return check_inventory_access(user, 'Edit')
