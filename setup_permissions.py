from user.models import Module, PermissionType, Role, RolePermission

def setup_hr_permissions():
    # Get HR module
    hr_module = Module.objects.get(name='HR')
    
    # Get permission types
    create_perm = PermissionType.objects.get(name='Create')
    delete_perm = PermissionType.objects.get(name='Delete')
    edit_perm = PermissionType.objects.get(name='Edit')
    view_perm = PermissionType.objects.get(name='View')
    
    # Define role permissions
    role_permissions = {
        'HR Manager': [create_perm, delete_perm, edit_perm, view_perm],  # Full HR access
        'HR ASSISTANT': [create_perm, edit_perm, view_perm],  # Everything except delete
        'Manager': [view_perm],  # View only
        'Admin': [create_perm, delete_perm, edit_perm, view_perm],  # Full HR access
    }
    
    print("Setting up HR permissions...")
    
    # Create permissions for each role
    for role_name, permissions in role_permissions.items():
        try:
            role = Role.objects.get(role_name=role_name)
            print(f"\nSetting permissions for {role_name}:")
            
            # First clear any existing HR permissions for this role
            RolePermission.objects.filter(role=role, module=hr_module).delete()
            
            # Create new permissions
            for perm_type in permissions:
                RolePermission.objects.create(
                    role=role,
                    module=hr_module,
                    permission_type=perm_type,
                    allowed=True
                )
                print(f"✓ Added {perm_type.name} permission")
                
        except Role.DoesNotExist:
            print(f"\nWarning: Role '{role_name}' does not exist")
            continue
        except Exception as e:
            print(f"\nError setting permissions for {role_name}: {str(e)}")
            continue

if __name__ == "__main__":
    setup_hr_permissions()