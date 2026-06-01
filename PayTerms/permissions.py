from user.utils import has_permission

# Aliases used in RolePermission.module names
_PAYTERMS_ALIASES = ['Masters Payment Terms', 'Payment Terms', 'PayTerms']


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


# Masters Payment Terms helpers
def can_view_payterms(user):
    return _any_alias_has_perm(user, _PAYTERMS_ALIASES, 'View')


def can_create_payterms(user):
    return _any_alias_has_perm(user, _PAYTERMS_ALIASES, 'Create')


def can_edit_payterms(user):
    return _any_alias_has_perm(user, _PAYTERMS_ALIASES, 'Edit')


def can_delete_payterms(user):
    return _any_alias_has_perm(user, _PAYTERMS_ALIASES, 'Delete')
