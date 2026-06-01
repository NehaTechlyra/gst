from user.utils import has_permission

# Aliases used in RolePermission.module names
_BANKING_ALIASES = ['Banking', 'banking']
_RECONCILIATION_ALIASES = ['Bank Reconciliation', 'bank reconciliation', 'Banking Bank Reconciliation']


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


# Banking Dashboard / Master helpers
def can_view_banking(user):
    return _any_alias_has_perm(user, _BANKING_ALIASES, 'View')


def can_create_banking(user):
    return _any_alias_has_perm(user, _BANKING_ALIASES, 'Create')


def can_edit_banking(user):
    return _any_alias_has_perm(user, _BANKING_ALIASES, 'Edit')


def can_delete_banking(user):
    return _any_alias_has_perm(user, _BANKING_ALIASES, 'Delete')


# Bank Reconciliation helpers
def can_view_reconciliation(user):
    return _any_alias_has_perm(user, _RECONCILIATION_ALIASES, 'View')


def can_create_reconciliation(user):
    return _any_alias_has_perm(user, _RECONCILIATION_ALIASES, 'Create')


def can_edit_reconciliation(user):
    return _any_alias_has_perm(user, _RECONCILIATION_ALIASES, 'Edit')


def can_delete_reconciliation(user):
    return _any_alias_has_perm(user, _RECONCILIATION_ALIASES, 'Delete')
