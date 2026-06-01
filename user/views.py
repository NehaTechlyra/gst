from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import userForm, userEditForm, PasswordUpdateForm, RoleForm
from .models import User, Module, PermissionType, RolePermission, Role
from django.core.paginator import Paginator
from django.db.models import Q
# from django.http.response import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.http import JsonResponse
from .permissions import (
    can_view_users, can_create_users, can_edit_users, can_delete_users,
    can_view_user_roles, can_create_user_roles, can_edit_user_roles, can_delete_user_roles
)
import logging
from Lyraerp.utils.redirect_utils import redirect_with_company
from .utils import _get_app_user_from_auth
from HR.models import Employee

logger = logging.getLogger(__name__)


def _ensure_category_type_modules(company_db):
    """
    Backfill missing module rows in older company DBs so role editor
    always shows Category/Type/Period Lock permissions.
    """
    from Lyraerp.utils.db_utils import (
        ensure_required_modules,
        ensure_sales_return_permissions,
        ensure_purchase_return_permissions,
        ensure_sales_performa_invoice_permissions,
    )
    ensure_required_modules(company_db)
    ensure_sales_return_permissions(company_db)
    ensure_purchase_return_permissions(company_db)
    ensure_sales_performa_invoice_permissions(company_db)



# def add_user(request):
#     # Permission: require create access to Masters Users
#     try:
#         if not (getattr(request.user, 'is_superuser', False) or can_create_users(request.user)):
#             messages.error(request, 'You do not have permission to create users.')
#             return redirect('user_list')
#     except Exception:
#         messages.error(request, 'You do not have permission to create users.')
#         return redirect('user_list')
    
#     if request.method == 'POST':
#         form = userForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "User added successfully.")
#             return redirect('user_list')  # redirect to user list page
#     else:
#         form = userForm()
#     return render(request, 'user/user_add.html', {'form': form})



#by sisira - updated to load permissions from the COMPANY database based on session variable, with enhanced logging and error handling. Also added module alias handling for better sidebar visibility control.
def add_user(request):
    # Permission: require create access to Masters Users
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_users(request.user)):
            messages.error(request, 'You do not have permission to create users.')
            return redirect_with_company(request, 'user_list')
    except Exception:
        messages.error(request, 'You do not have permission to create users.')
        return redirect_with_company(request, 'user_list')
    
    company_db = getattr(request, 'company_db', 'default')

    if request.method == 'POST':
        form = userForm(request.POST, db_alias=company_db)
        if form.is_valid():
            # ✅ Save to current database (company DB)
            user = form.save(commit=False)
            company_db = getattr(request, 'company_db', 'default')
            
            # ✅ CRITICAL FIX: Ensure the role has a company assigned
            if user.usr_roleid and not user.usr_roleid.company_id:
                # Get the company from session
                company_id = request.session.get('company_id')
                if company_id:
                    from company.models import Company
                    try:
                        company = Company.objects.using('default').get(id=company_id)
                        
                        # Update role to have company
                        user.usr_roleid.company = company
                        user.usr_roleid.save(using=company_db, update_fields=['company'])
                        
                        # Also update in master DB
                        Role.objects.using('default').filter(
                            id=user.usr_roleid.id
                        ).update(company_id=company_id)
                        
                        logger.info(f"[OK] Updated role {user.usr_roleid.id} with company {company_id}")
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to update role company: {e}")
            
            # Determine company from session; prefer custom_user_id (login owner)
            company_id = request.session.get('company_id')
            session_custom_user_id = request.session.get('custom_user_id')
            if session_custom_user_id:
                try:
                    # Read admin user from master DB to get authoritative company
                    admin_user = User.objects.using('default').get(pk=session_custom_user_id)
                    if getattr(admin_user, 'company_id', None):
                        company_id = admin_user.company_id
                except Exception as e:
                    logger.debug(f"[DEBUG] Could not resolve admin from session custom_user_id: {e}")
            if not company_id and getattr(user, 'usr_roleid', None) and user.usr_roleid.company_id:
                company_id = user.usr_roleid.company_id
            company = None
            if company_id:
                from company.models import Company
                try:
                    company = Company.objects.using('default').get(id=company_id)
                    user.company = company
                except Exception as e:
                    logger.error(f"[ERROR] Failed to set user.company from session: {e}")

            company_db = getattr(request, 'company_db', 'default')

            # Prevent duplicate username in:
            # 1) current company DB
            # 2) master DB globally (any company)
            username_to_check = (user.usr_name or '').strip()
            if username_to_check:
                exists_in_company_db = User.objects.using(company_db).filter(
                    usr_name__iexact=username_to_check
                ).exists()
                exists_in_master_db = User.objects.using('default').filter(
                    usr_name__iexact=username_to_check
                ).exists()
                if exists_in_company_db or exists_in_master_db:
                    form.add_error('usr_name', f"Username '{username_to_check}' already exists.")
                    messages.error(
                        request,
                        f"Username '{username_to_check}' already exists."
                    )
                    return render(request, 'user/user_add.html', {'form': form})

            # Prevent duplicate email in:
            # 1) current company DB
            # 2) master DB globally (any company)
            email_to_check = (user.usr_mail or '').strip()
            if email_to_check:
                email_exists_in_company_db = User.objects.using(company_db).filter(
                    usr_mail__iexact=email_to_check
                ).exists()
                email_exists_in_master_db = User.objects.using('default').filter(
                    usr_mail__iexact=email_to_check
                ).exists()
                if email_exists_in_company_db or email_exists_in_master_db:
                    form.add_error('usr_mail', f"Email '{email_to_check}' already exists.")
                    messages.error(
                        request,
                        f"Email '{email_to_check}' already exists."
                    )
                    return render(request, 'user/user_add.html', {'form': form})

            # Enforce single admin per company (in company DB)
            if getattr(user, 'is_admin', False) and company_id:
                try:
                    existing = User.objects.using(company_db).filter(company_id=company_id, is_admin=True)
                    if existing.exists():
                        messages.error(request, 'An admin already exists for this company.')
                        return redirect_with_company(request, 'user_list')
                except Exception as e:
                    logger.error(f"[ERROR] Admin uniqueness check failed: {e}")

            # Always save explicitly to the active company database first.
            user.save(using=company_db)
            
            # ✅ ALSO save to master database
            company_db = getattr(request, 'company_db', 'default')
            if company_db != 'default':
                try:
                    defaults = {
                        'usr_fname': user.usr_fname,
                        'usr_mail': user.usr_mail,
                        'usr_phn': user.usr_phn,
                        'usr_pwd': user.usr_pwd,
                        'is_admin': user.is_admin,
                        'company_id': company_id,
                    }

                    # Ensure Role exists in master DB and set the FK correctly
                    master_role = None
                    if getattr(user, 'usr_roleid', None) and company_id:
                        try:
                            master_role, _ = Role.objects.using('default').get_or_create(
                                role_name=user.usr_roleid.role_name,
                                company_id=company_id,
                                defaults={'description': getattr(user.usr_roleid, 'description', '') or ''}
                            )
                        except Exception as e:
                            logger.error(f"[ERROR] Failed to ensure master Role: {e}")

                    if master_role:
                        defaults['usr_roleid'] = master_role

                    User.objects.using('default').update_or_create(
                        usr_name=user.usr_name,
                        company_id=company_id,
                        defaults=defaults
                    )
                    logger.info(f"[OK] User '{user.usr_name}' synced to master database")
                except Exception as e:
                    logger.error(f"[ERROR] Failed to sync user to master: {e}")
                    
                # Also ensure a Django auth user exists in master DB with the same hashed password
                try:
                    from django.contrib.auth.models import User as DjangoAuthUser
                    auth_defaults = {
                        'first_name': user.usr_fname or '',
                        'email': user.usr_mail or '',
                        'is_active': True,
                        'is_staff': bool(user.is_admin),
                    }
                    # Assign hashed password directly if available
                    if getattr(user, 'usr_pwd', None):
                        auth_defaults['password'] = user.usr_pwd

                    DjangoAuthUser.objects.using('default').update_or_create(
                        username=user.usr_name,
                        defaults=auth_defaults
                    )
                except Exception as e:
                    logger.error(f"[ERROR] Failed to sync Django auth_user: {e}")
            
            messages.success(request, "User added successfully.")
            return redirect_with_company(request, 'user_list')
    else:
        form = userForm(db_alias=company_db)
    return render(request, 'user/user_add.html', {'form': form})


def user_list(request):
    # Permission: require view access to Masters Users
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_users(request.user)):
            messages.error(request, 'You do not have permission to view users.')
            return redirect_with_company(request, 'home')
    except Exception:
        messages.error(request, 'You do not have permission to view users.')
        return redirect_with_company(request, 'home')
    
    search_query = request.GET.get('q', '')
    users = User.objects.all().order_by('id')
    paginator = Paginator(users, 10)
    if search_query:
        users = users.filter(
            Q(usr_name__icontains=search_query) |
            Q(usr_mail__icontains=search_query) |
            Q(usr_phn__icontains=search_query)
        )

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    context = {
        "users": users_page,
        "search_query": search_query,
        "can_create": (getattr(request.user, 'is_superuser', False) or can_create_users(request.user)),
        "can_edit": (getattr(request.user, 'is_superuser', False) or can_edit_users(request.user)),
        "can_delete": (getattr(request.user, 'is_superuser', False) or can_delete_users(request.user)),
    }
    return render(request, 'user/user_list.html', context)


@login_required
@login_required
def user_profile(request):
    app_user = _get_app_user_from_auth(request.user)
    if not app_user:
        messages.error(request, "User profile not found.")
        return redirect_with_company(request, 'index')

    can_edit = bool(
        getattr(request.user, 'is_superuser', False) or can_edit_users(request.user)
    )

    # Try to find matching Employee so we can show employee code when available.
    # Strategy: email -> phone -> name (first + last) to be more resilient to differing data.
    employee_obj = None
    try:
        usr_mail = getattr(app_user, 'usr_mail', None)
        usr_phn = getattr(app_user, 'usr_phn', None)
        usr_fname = getattr(app_user, 'usr_fname', None) or ''

        if usr_mail:
            employee_obj = Employee.objects.filter(email__iexact=usr_mail).first()

        if not employee_obj and usr_phn:
            employee_obj = Employee.objects.filter(phone__iexact=usr_phn).first()

        if not employee_obj and usr_fname:
            # Try matching by first/last name. Split usr_fname into parts.
            parts = [p.strip() for p in usr_fname.split() if p.strip()]
            if len(parts) == 1:
                employee_obj = Employee.objects.filter(first_name__iexact=parts[0]).first()
            elif len(parts) >= 2:
                first = parts[0]
                last = ' '.join(parts[1:])
                employee_obj = Employee.objects.filter(first_name__iexact=first, last_name__iexact=last).first()
    except Exception:
        employee_obj = None

    # Also prepare company-scoped user instance and forms so profile can embed edit/password forms
    company_db = getattr(request, 'company_db', 'default')
    company_user = None
    try:
        # Prefer matching by username, fallback to email
        if getattr(app_user, 'usr_name', None):
            company_user = User.objects.using(company_db).filter(usr_name=app_user.usr_name).first()
        if not company_user and getattr(app_user, 'usr_mail', None):
            company_user = User.objects.using(company_db).filter(usr_mail__iexact=app_user.usr_mail).first()
    except Exception:
        company_user = None

    edit_form = None
    pwd_form = PasswordUpdateForm()
    if company_user:
        try:
            edit_form = userEditForm(instance=company_user, db_alias=company_db)
        except Exception:
            edit_form = userEditForm(instance=company_user)

    # Build a compact permissions summary (grouped by module) for the profile dashboard
    permissions_by_module = {}
    try:
        role_ref = getattr(app_user, 'usr_roleid', None)
        role_id = getattr(role_ref, 'id', None) if role_ref else None
        if role_id:
            # Try to resolve role in company DB
            try:
                company_role = Role.objects.using(company_db).get(pk=role_id)
            except Exception:
                # Fallback: try matching by role_name
                role_name = getattr(role_ref, 'role_name', None)
                company_role = Role.objects.using(company_db).filter(role_name=role_name).first() if role_name else None

            if company_role:
                perms_qs = RolePermission.objects.using(company_db).filter(role=company_role, allowed=True).select_related('module', 'permission_type')
                for rp in perms_qs:
                    mod_name = getattr(rp.module, 'name', None) or getattr(rp.module, 'module_name', None) or f"Module {getattr(rp.module,'id', '')}"
                    permissions_by_module.setdefault(mod_name, []).append(getattr(rp.permission_type, 'name', '') or '')
    except Exception:
        permissions_by_module = {}

    # Convert to list for safer template iteration
    permissions_list = [{'module': m, 'perms': v} for m, v in permissions_by_module.items()]
    return render(request, 'user/user_profile.html', {
        'app_user': app_user,
        'employee': employee_obj,
        'company_user': company_user,
        'edit_form': edit_form,
        'password_form': pwd_form,
        'can_edit': can_edit,
    })


def user_edit(request, pk):
    company_db = getattr(request, 'company_db', 'default')
    user_instance = None
    try:
        user_instance = get_object_or_404(User.objects.using(company_db), pk=pk)
    except Exception:
        # If this was an AJAX/modal request, try to fall back to master DB to render a fragment
        if request.method == 'GET' and request.GET.get('modal') == '1':
            user_instance = User.objects.using('default').filter(pk=pk).first()
        else:
            raise

    can_edit = False
    try:
        can_edit = bool(getattr(request.user, 'is_superuser', False) or can_edit_users(request.user))
    except Exception:
        can_edit = False

    is_self = False
    try:
        app_user = _get_app_user_from_auth(request.user)
        if app_user and user_instance:
            is_self = (
                getattr(app_user, 'usr_name', None) == getattr(user_instance, 'usr_name', None)
            )
    except Exception:
        is_self = False

    edit_form = userEditForm(instance=user_instance, db_alias=company_db if user_instance and getattr(user_instance, '_state', None) and getattr(user_instance._state, 'db', None) else 'default')
    pwd_form = PasswordUpdateForm()

    # If requested as a modal fragment, render a partial containing only the forms
    if request.method == 'GET' and request.GET.get('modal') == '1':
        return render(request, 'user/_user_edit_fragment.html', {
            'form': edit_form,
            'password_form': pwd_form,
            'app_user': user_instance,
        })

    if request.method == 'POST':
        if not (can_edit or is_self):
            messages.error(request, 'You do not have permission to edit users.')
            return redirect_with_company(request, 'license_restricted')

        # keep track of where to redirect after successful save
        next_param = request.POST.get('next') or request.GET.get('next')
        if 'update_profile' in request.POST:
            edit_form = userEditForm(request.POST, instance=user_instance, db_alias=company_db)
            pwd_form = PasswordUpdateForm()  # blank for rendering
            if edit_form.is_valid():
                # Save using the company DB explicitly: ModelForm.save doesn't accept 'using',
                # so save with commit=False then save the instance with the desired DB.
                updated_user = edit_form.save(commit=False)
                try:
                    updated_user.save(using=company_db)
                except Exception:
                    # Fallback to default save if company DB save fails
                    updated_user.save()
                try:
                    edit_form.save_m2m()
                except Exception:
                    # Some forms may not have m2m; ignore failures here
                    pass
                messages.success(request, "User edited successfully.")
                if next_param == 'profile':
                    return redirect_with_company(request, 'user_profile')
                return redirect_with_company(request, 'user_list')
        elif 'update_password' in request.POST:
            pwd_form = PasswordUpdateForm(request.POST)
            edit_form = userEditForm(instance=user_instance)  # prefill with db
            if pwd_form.is_valid():
                new_password = pwd_form.cleaned_data['usr_pwd']
                user_instance.usr_pwd = make_password(new_password)
                user_instance.save(using=company_db)
                # Also sync password to master DB and Django auth user so login works
                try:
                    # Update master custom user record
                    if company_db != 'default':
                        from user.models import User as MasterUser
                        MasterUser.objects.using('default').filter(usr_name=user_instance.usr_name).update(usr_pwd=user_instance.usr_pwd)

                    # Update Django auth user in master DB
                    from django.contrib.auth.models import User as DjangoAuthUser
                    try:
                        django_user = DjangoAuthUser.objects.using('default').get(username=user_instance.usr_name)
                        django_user.set_password(new_password)
                        django_user.save(using='default')
                    except DjangoAuthUser.DoesNotExist:
                        # Create or update if missing
                        DjangoAuthUser.objects.using('default').update_or_create(
                            username=user_instance.usr_name,
                            defaults={'email': getattr(user_instance, 'usr_mail', ''), 'is_active': True, 'password': user_instance.usr_pwd}
                        )
                except Exception as e:
                    logger.error(f"[ERROR] Failed to sync password to master auth: {e}")
                messages.success(request, "Password updated successfully.")
                if next_param == 'profile':
                    return redirect_with_company(request, 'user_profile')
                return redirect_with_company(request, 'user_list')
    else:
        if not (can_edit or is_self):
            messages.error(request, 'You do not have permission to edit users.')
            return redirect_with_company(request, 'license_restricted')

        # GET - normal population
        edit_form = userEditForm(instance=user_instance, db_alias=company_db)
        pwd_form = PasswordUpdateForm()

    return render(request, 'user/user_edit.html', {
        'form': edit_form,
        'password_form': pwd_form,
    })

@require_POST
def user_delete(request, pk):
    # Permission: require delete access to Masters Users
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_users(request.user)):
            messages.error(request, 'You do not have permission to delete users.')
            return redirect_with_company(request, 'user_list')
    except Exception:
        messages.error(request, 'You do not have permission to delete users.')
        return redirect_with_company(request, 'user_list')
    
    user_instance = get_object_or_404(User, pk=pk)
    user_instance.delete()
    messages.success(request, "User deleted successfully.")
    return redirect_with_company(request, 'user_list')


def roles_view(request, pk=None):
    # Permission: require view access to Masters User Roles
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_user_roles(request.user)):
            messages.error(request, 'You do not have permission to view user roles.')
            return redirect_with_company(request, 'home')
    except Exception:
        messages.error(request, 'You do not have permission to view user roles.')
        return redirect_with_company(request, 'home')
    
    # Determine company DB early so all Role/RolePermission ops use correct DB
    company_db = getattr(request, 'company_db', 'default')
    
    # Ensure all required modules exist (but don't backfill permissions)
    from Lyraerp.utils.db_utils import ensure_required_modules
    ensure_required_modules(company_db)

    if pk:
        # Permission: require edit access to Masters User Roles for editing
        try:
            if not (getattr(request.user, 'is_superuser', False) or can_edit_user_roles(request.user)):
                messages.error(request, 'You do not have permission to edit user roles.')
                return redirect_with_company(request, 'roles_list')
        except Exception:
            messages.error(request, 'You do not have permission to edit user roles.')
            return redirect_with_company(request, 'roles_list')
        # Fetch role from the company database
        try:
            role_instance = Role.objects.using(company_db).get(pk=pk)
        except Role.DoesNotExist:
            role_instance = get_object_or_404(Role, pk=pk)
    else:
        # Permission: require create access to Masters User Roles for creating new
        if request.method == 'POST':
            try:
                if not (getattr(request.user, 'is_superuser', False) or can_create_user_roles(request.user)):
                    messages.error(request, 'You do not have permission to create user roles.')
                    return redirect_with_company(request, 'roles_list')
            except Exception:
                messages.error(request, 'You do not have permission to create user roles.')
                return redirect_with_company(request, 'roles_list')
        role_instance = None

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"POST request received for roles_view. Data: {request.POST}")
        
        form = RoleForm(request.POST, instance=role_instance)
        if form.is_valid():
            # Save role into the company database
            role = form.save(commit=False)
            try:
                role.save(using=company_db)
            except Exception:
                # fallback to default save
                role.save()
            logger.info(f"Role saved successfully: {role.role_name}")
            # Save role and its permissions. Support creating a new Module and PermissionTypes
            # from the front-end by accepting 'new_module_name' and 'new_permission_types' (comma-separated)
            modules = Module.objects.using(company_db).all()
            permission_types = PermissionType.objects.using(company_db).all()

            # Clear existing RolePermissions for this role (company DB)
            RolePermission.objects.using(company_db).filter(role=role).delete()

            # Save RolePermissions from the submitted checkboxes (existing modules/perm types)
            for module in modules:
                for perm_type in permission_types:
                    checkbox_name = f'permissions_{module.id}_{perm_type.id}'
                    if checkbox_name in request.POST:
                        RolePermission.objects.using(company_db).create(
                            role=role,
                            module=module,
                            permission_type=perm_type,
                            allowed=True
                        )

            # Create a new Module (if provided) and PermissionType(s) and assign them to the role
            # new_module_name = request.POST.get('new_module_name', '').strip()
            # new_perm_raw = request.POST.get('new_permission_types', '').strip()
            # if new_module_name:
            #     # get_or_create makes this idempotent
            #     new_module, _ = Module.objects.get_or_create(name=new_module_name)
            #     if new_perm_raw:
            #         # accept comma-separated list like: "View, Add, Edit"
            #         perm_names = [p.strip() for p in new_perm_raw.split(',') if p.strip()]
            #         for pname in perm_names:
            #             perm_obj, _ = PermissionType.objects.get_or_create(name=pname)
            #             # Create RolePermission for this new module and permission type
            #             # Use get_or_create in case unique_together prevents duplicate
            #             RolePermission.objects.get_or_create(
            #                 role=role,
            #                 module=new_module,
            #                 permission_type=perm_obj,
            #                 defaults={'allowed': True}
            #             )

            # If this is an AJAX request, return JSON so the front-end can update without reload
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest') or (request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest')
            success_msg = f"Role '{role.role_name}' saved successfully."
            if is_ajax:
                return JsonResponse({'status': 'success', 'message': success_msg})

            messages.success(request, success_msg)
            return redirect_with_company(request, 'roles_list')  # Redirect to roles listing after save
        else:
            # Show form errors as messages
            # If AJAX, return a JSON response with error details
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest') or (request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest')
            if is_ajax:
                error_dict = {}
                for field, errors in form.errors.items():
                    label = form.fields[field].label if field in form.fields else field
                    error_dict[field] = [str(e) for e in errors]
                return JsonResponse({'status': 'error', 'errors': error_dict}, status=400)

            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"{label}: {error}")
    else:
        form = RoleForm(instance=role_instance)

    modules = Module.objects.using(company_db).all().order_by('name')
    permission_types = PermissionType.objects.using(company_db).all().order_by('id')

    # Populate role_permissions dict for checkboxes when editing
    role_permissions = {}
    if role_instance:
        rp_qs = RolePermission.objects.using(company_db).filter(role=role_instance)
        for rp in rp_qs:
            role_permissions.setdefault(rp.module.id, {})[rp.permission_type.id] = True

    return render(request, 'user/roles.html', {
        'form': form,
        'modules': modules,
        'permission_types': permission_types,
        'role_permissions': role_permissions,
    })

def roles_list(request):
    # Permission: require view access to Masters User Roles
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_user_roles(request.user)):
            messages.error(request, 'You do not have permission to view user roles.')
            return redirect_with_company(request, 'home')
    except Exception:
        messages.error(request, 'You do not have permission to view user roles.')
        return redirect_with_company(request, 'home')
    
    roles = Role.objects.all().order_by('id')  # Order by id for consistent listing

    search_query = request.GET.get('q', '')
    
    paginator = Paginator(roles, 10)
    if search_query:
        roles = roles.filter(
            Q(role_name__icontains=search_query) |
            Q(description__icontains=search_query) 
        )

    paginator = Paginator(roles, 10)
    page_number = request.GET.get('page')
    roles_page = paginator.get_page(page_number)
    context = {
        "roles": roles_page,
        "search_query": search_query,
        "can_create": (getattr(request.user, 'is_superuser', False) or can_create_user_roles(request.user)),
        "can_edit": (getattr(request.user, 'is_superuser', False) or can_edit_user_roles(request.user)),
        "can_delete": (getattr(request.user, 'is_superuser', False) or can_delete_user_roles(request.user)),
    }
    return render(request, 'user/roles_list.html', context)
    # return render(request, 'user/roles_list.html', {'roles': roles})

@require_POST
def role_delete(request, pk):
    # Permission: require delete access to Masters User Roles
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_user_roles(request.user)):
            messages.error(request, 'You do not have permission to delete user roles.')
            return redirect_with_company(request, 'roles_list')
    except Exception:
        messages.error(request, 'You do not have permission to delete user roles.')
        return redirect_with_company(request, 'roles_list')
    
    role_instance = get_object_or_404(Role, pk=pk)
    role_instance.delete()
    messages.success(request, "Role deleted successfully.")
    return redirect_with_company(request, 'roles_list')

# @require_POST
# def module_delete(request, pk):
#     """Delete a module and its associated permissions."""
#     # TODO: Add proper permission check here
#     if not request.user.is_authenticated:
#         return HttpResponseForbidden()

#     module = get_object_or_404(Module, pk=pk)
#     module_name = module.name
#     module.delete()  # This will cascade delete related RolePermission rows

#     is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest')
#     if is_ajax:
#         return JsonResponse({
#             'status': 'success',
#             'message': f'Module "{module_name}" deleted successfully'
#         })
    
#     messages.success(request, f'Module "{module_name}" deleted successfully')
#     return redirect('roles_list')

# @require_POST 
# def module_edit(request, pk):
#     """Edit a module's name."""
#     # TODO: Add proper permission check here
#     if not request.user.is_authenticated:
#         return HttpResponseForbidden()

#     module = get_object_or_404(Module, pk=pk)
#     new_name = request.POST.get('module_name', '').strip()
    
#     if not new_name:
#         error = 'Module name cannot be empty'
#         if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#             return JsonResponse({'status': 'error', 'message': error}, status=400)
#         messages.error(request, error)
#         return redirect('roles_list')

#     try:
#         module.name = new_name
#         module.save()
#         msg = f'Module renamed to "{new_name}"'
        
#         if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#             return JsonResponse({'status': 'success', 'message': msg})
            
#         messages.success(request, msg)
#         return redirect('roles_list')
        
#     except Exception as e:
#         error = f'Failed to rename module: {str(e)}'
#         if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#             return JsonResponse({'status': 'error', 'message': error}, status=400)
#         messages.error(request, error)
#         return redirect('roles_list')


from django.http import JsonResponse

def validate_user_field(request):
    """Real-time uniqueness check for username and email."""
    field = request.GET.get('field')
    value = (request.GET.get('value') or '').strip()
    
    if not field or not value:
        return JsonResponse({'available': True})
    
    company_db = getattr(request, 'company_db', 'default')
    company_id = request.session.get('company_id')
    
    exists = False
    
    if field == 'usr_name':
        exists = (
            User.objects.using(company_db).filter(usr_name__iexact=value).exists() or
            User.objects.using('default').filter(usr_name__iexact=value).exists()
        )
        error_msg = f"Username '{value}' already exists."
        
    elif field == 'usr_mail':
        exists = (
            User.objects.using(company_db).filter(usr_mail__iexact=value).exists() or
            User.objects.using('default').filter(usr_mail__iexact=value).exists()
        )
        error_msg = f"Email '{value}' already exists."
    else:
        return JsonResponse({'available': True})
    
    return JsonResponse({
        'available': not exists,
        'message': error_msg if exists else ''
    })
