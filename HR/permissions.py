from user.utils import has_permission

# Define strict HR module names for permissions
_DASHBOARD_ALIASES = ['HR Dashboard', 'HR Management']
_EMPLOYEE_ALIASES = ['HR Employee', 'HR Employees']
_RECRUIT_ALIASES = ['HR Recruitment', 'HR Recruitments']
_MASTER_ALIASES = ['HR Master', 'HR Masters', 'HR masters']


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


def check_hr_module_access(user):
    """Base check for HR module access. Accepts any HR-prefixed module."""
    return _any_alias_has_perm(user, _DASHBOARD_ALIASES + _EMPLOYEE_ALIASES + _RECRUIT_ALIASES + _MASTER_ALIASES, perm='View')


def check_dashboard_access(user, perm='View'):
    """Check if user has access to HR dashboard with specific permission."""
    return _any_alias_has_perm(user, _DASHBOARD_ALIASES, perm=perm)


def check_employee_access(user, perm='View'):
    """Check if user has access to employee management with specific permission."""
    return _any_alias_has_perm(user, _EMPLOYEE_ALIASES, perm=perm)


def check_recruitment_access(user, perm='View'):
    """Check if user has access to recruitment section with specific permission."""
    return _any_alias_has_perm(user, _RECRUIT_ALIASES, perm=perm)


def check_master_access(user, perm='View'):
    """Check if user has access to HR master data with specific permission."""
    return _any_alias_has_perm(user, _MASTER_ALIASES, perm=perm)
