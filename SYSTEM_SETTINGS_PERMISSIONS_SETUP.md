# System Settings Module - Role-Based Permissions Setup

## Overview
The system settings module now has complete role-based access control with the following 5 sub-modules:

1. **System settings** - Main system settings access
2. **System settings Company** - Company configuration
3. **System settings Email Configuration** - Email setup
4. **System settings Email Templates** - Email template management
5. **System settings SMS Configuration** - SMS setup
6. **System settings SMS Templates** - SMS template management

## Files Modified/Created

### Permissions Files Created:
- `system_settings/permissions.py` - View, Create, Edit, Delete checks
- `email_config/permissions.py` - View, Create, Edit, Delete checks
- `sms_config/permissions.py` - View, Create, Edit, Delete checks
- `company/permissions.py` - View, Create, Edit, Delete checks
- `email_templates/permissions.py` - View, Create, Edit, Delete checks
- `sms_templates/permissions.py` - View, Create, Edit, Delete checks

### Views Updated (Permission Checks Added):
- `system_settings/views.py` - settings_page()
- `email_config/views.py` - all CRUD operations
- `sms_config/views.py` - all CRUD operations
- `company/views.py` - all CRUD operations
- `email_templates/views.py` - all CRUD operations
- `sms_templates/views.py` - all CRUD operations

### Setup Scripts:
- `setup_permissions.py` - Updated with system settings module setup
- `setup_system_settings_perms.py` - Standalone script for setup

## How to Setup Permissions

### Option 1: Using Django Shell (Recommended)

```bash
# Open Django shell
python manage.py shell

# Run the setup
>>> from setup_system_settings_perms import setup_system_settings_modules, setup_system_settings_permissions
>>> setup_system_settings_modules()
>>> setup_system_settings_permissions()
```

### Option 2: Run Setup Script

```bash
python setup_system_settings_perms.py
```

### Option 3: Using setup_permissions.py

```bash
python manage.py shell

>>> from setup_permissions import setup_system_settings_modules, setup_system_settings_permissions
>>> setup_system_settings_modules()
>>> setup_system_settings_permissions()
```

## What Gets Created

The setup script will:

1. **Create 6 Module entries** in the database:
   - System settings
   - System settings Company
   - System settings Email Configuration
   - System settings Email Templates
   - System settings SMS Configuration
   - System settings SMS Templates

2. **Assign Permissions for Admin Role**:
   - View, Create, Edit, Delete on all 6 modules

3. **Optional: Assign Permissions for other roles**:
   - HR Manager: View, Create, Edit, Delete
   - Manager: View only

## Permission Hierarchy

When users access any system settings feature, the permission check follows this flow:

```
User Request
    ↓
Is user Superuser? → YES → Grant Access
    ↓ NO
Has View permission? → NO → Redirect + Error Message
    ↓ YES
Specific Operation (Create/Edit/Delete)?
    ↓
Check specific permission (Create/Edit/Delete)
    ↓
If NO permission → Redirect + Error Message
    ↓ YES
Grant Access
```

## How Permissions Are Checked in Views

Example from `email_config/views.py`:

```python
@login_required
def email_config_create(request):
    # Permission check - require create access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_email_config(request.user)):
            messages.error(request, 'You do not have permission to create Email Configuration.')
            return redirect('email_config_list')
    except Exception:
        messages.error(request, 'You do not have permission to create Email Configuration.')
        return redirect('email_config_list')
    
    # Rest of the view logic...
```

## Adding More Roles/Permissions

To add permissions for other roles, edit `setup_system_settings_perms.py`:

```python
role_permissions = {
    'Admin': [create_perm, delete_perm, edit_perm, view_perm],
    'Your Role': [view_perm, create_perm, edit_perm],  # Add your role
}
```

Then run the setup again.

## Testing Permissions

1. Login with a user that has `Manager` role
2. Try to access: `/system_settings/settings/`
3. Should see the page (View permission)
4. Try to click "Add Email Configuration" 
5. Should be redirected with error message (No Create permission)

## Troubleshooting

### Modules not showing in admin?
- Run setup script to create the Module entries
- Refresh the admin page

### Still getting access to restricted features?
- Check if user is superuser (superusers bypass all checks)
- Verify RolePermission entries in admin
- Clear browser cache and re-login

### Permission denied for Admin role?
- Run setup script again to recreate permissions
- Check if 'Admin' role exists in the database

## Summary

✅ Role-based access control is fully implemented
✅ All 6 system settings modules are protected
✅ View, Create, Edit, Delete operations are checked
✅ Setup script automates permission creation
✅ Superusers automatically get full access
