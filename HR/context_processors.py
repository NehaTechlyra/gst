from .permissions import (
    check_dashboard_access, check_employee_access,
    check_recruitment_access, check_master_access
)

def hr_permissions(request):
    """Context processor that adds HR-specific permissions to the template context."""
    user = getattr(request, 'user', None)
    # Superusers should see all HR sections with full permissions
    try:
        if user and getattr(user, 'is_superuser', False):
            return {
                'can_view_dashboard': True,
                'can_create_dashboard': True,
                'can_edit_dashboard': True,
                'can_delete_dashboard': True,
                'can_view_employees': True,
                'can_create_employees': True,
                'can_edit_employees': True,
                'can_delete_employees': True,
                'can_view_recruitment': True,
                'can_create_recruitment': True,
                'can_edit_recruitment': True,
                'can_delete_recruitment': True,
                'can_view_master': True,
                'can_create_master': True,
                'can_edit_master': True,
                'can_delete_master': True,
            }
    except Exception:
        pass

    # For regular users, check each permission type
    return {
        'can_view_dashboard': check_dashboard_access(user, 'View'),
        'can_create_dashboard': check_dashboard_access(user, 'Create'),
        'can_edit_dashboard': check_dashboard_access(user, 'Edit'),
        'can_delete_dashboard': check_dashboard_access(user, 'Delete'),
        'can_view_employees': check_employee_access(user, 'View'),
        'can_create_employees': check_employee_access(user, 'Create'),
        'can_edit_employees': check_employee_access(user, 'Edit'),
        'can_delete_employees': check_employee_access(user, 'Delete'),
        'can_view_recruitment': check_recruitment_access(user, 'View'),
        'can_create_recruitment': check_recruitment_access(user, 'Create'),
        'can_edit_recruitment': check_recruitment_access(user, 'Edit'),
        'can_delete_recruitment': check_recruitment_access(user, 'Delete'),
        'can_view_master': check_master_access(user, 'View'),
        'can_create_master': check_master_access(user, 'Create'),
        'can_edit_master': check_master_access(user, 'Edit'),
        'can_delete_master': check_master_access(user, 'Delete'),
    }