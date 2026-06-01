# by adarsh - role based permission for Email Templates
from user.utils import has_permission

# Aliases used in RolePermission.module names
_EMAIL_TEMPLATES_ALIASES = ['System settings Email Templates', 'System settings Email templates']


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


# Email Templates helpers - by adarsh
def can_view_email_templates(user):
    return _any_alias_has_perm(user, _EMAIL_TEMPLATES_ALIASES, 'View')


def can_create_email_templates(user):
    return _any_alias_has_perm(user, _EMAIL_TEMPLATES_ALIASES, 'Create')


def can_edit_email_templates(user):
    return _any_alias_has_perm(user, _EMAIL_TEMPLATES_ALIASES, 'Edit')


def can_delete_email_templates(user):
    return _any_alias_has_perm(user, _EMAIL_TEMPLATES_ALIASES, 'Delete')
