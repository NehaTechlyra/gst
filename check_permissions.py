from user.models import Module, PermissionType, Role, RolePermission

def check_hr_permissions():
    print("Checking HR module permissions...")
    
    # Check if HR module exists
    hr_module = Module.objects.filter(name='HR').first()
    if not hr_module:
        print("WARNING: 'HR' module does not exist")
    else:
        print("✓ HR module exists")
        
    # Check permission types
    perm_types = PermissionType.objects.all()
    print("\nPermission Types:")
    if not perm_types.exists():
        print("WARNING: No permission types defined")
    else:
        for pt in perm_types:
            print(f"- {pt.name}")
            
    # Check roles
    roles = Role.objects.all()
    print("\nRoles:")
    if not roles.exists():
        print("WARNING: No roles defined")
    else:
        for role in roles:
            print(f"\nRole: {role.role_name}")
            if hr_module:
                # Check HR permissions for this role
                role_perms = RolePermission.objects.filter(
                    role=role,
                    module=hr_module
                )
                if role_perms.exists():
                    print("HR Permissions:")
                    for rp in role_perms:
                        print(f"- {rp.permission_type.name}: {'Allowed' if rp.allowed else 'Not Allowed'}")
                else:
                    print("WARNING: No HR permissions set for this role")

if __name__ == "__main__":
    check_hr_permissions()