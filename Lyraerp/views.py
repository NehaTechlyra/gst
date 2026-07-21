"""
COMPLETE LOGIN & SIGNUP VIEWS
Fixed: Trial fields and contact person are synced to company DB on first login,
after the database is created and migrated.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction, connections, connection
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
from django import forms
import logging
from django_countries import countries
import re
from django.conf import settings

from user.models import User as CustomUser, Role, Module, RolePermission, PermissionType
from company.models import Company
from company.utils import get_company_logo_base64
from Lyraerp.utils.db_utils import (
    generate_db_name,
    generate_registration_code as generate_company_code,
    create_physical_database,
    migrate_company_database,
    register_database,
    sync_auth_user,
    populate_permission_types,
    populate_modules_from_license,
    create_admin_role_permissions,
    delete_company_database,
    sync_company_record,                   
    sync_contact_person_both_ways,         
)
from Lyraerp.utils.async_migrations import (
    run_migrations_async,
    run_critical_migrations,
    run_company_setup_async,
    get_migration_status,
)
from Lyraerp.utils.email_utils import send_registration_email
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm

logger = logging.getLogger(__name__)


class UsernameOrEmailPasswordResetForm(PasswordResetForm):
    """
    Allow the password reset field to accept either a real email address
    or an application username and resolve it to the user's email.
    """

    email = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={'autocomplete': 'email'}),
    )

    def __init__(self, *args, company_code=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_code = company_code

    def get_users(self, email_or_username):
        identifier = (email_or_username or '').strip()
        if not identifier:
            return super().get_users(identifier)

        if '@' in identifier:
            return super().get_users(identifier)

        user_qs = CustomUser.objects.using('default').filter(usr_name__iexact=identifier)

        if self.company_code:
            user_qs = user_qs.filter(company__company_code=self.company_code)

        custom_user = user_qs.order_by('id').first()
        if custom_user and custom_user.usr_mail:
            return super().get_users(custom_user.usr_mail.strip())

        django_user = DjangoUser.objects.using('default').filter(username__iexact=identifier).first()
        if django_user and django_user.email:
            return super().get_users(django_user.email.strip())

        return super().get_users(identifier)


def get_license_modules(company):
    """Extract allowed modules from license key. Returns None for full access."""
    return None


# ==============================================================================
# CUSTOM PASSWORD RESET VIEW (injects company branding into email)
# ==============================================================================

class CompanyPasswordResetView(PasswordResetView):
    """
    Extends Django's PasswordResetView to inject company_name and
    company_logo_base64 into the email context so the password reset
    email can display the company's own branding instead of hardcoded text.
    Works for both /password-reset/ and /<company_code>/password-reset/.
    """
    template_name = 'registration/password_reset_form.html'
    html_email_template_name = 'registration/password_reset_email.html'
    form_class = UsernameOrEmailPasswordResetForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company_code'] = self.kwargs.get('company_code')
        return kwargs

    def get_extra_email_context(self):
        extra = super().get_extra_email_context() or {}
        company_code = self.kwargs.get('company_code')
        company_name = settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'LyraERP'
        company_logo_base64 = None
        if company_code:
            try:
                company = Company.objects.using('default').get(company_code=company_code)
                company_name = company.name
                company_logo_base64 = get_company_logo_base64(company)
            except Company.DoesNotExist:
                pass
        extra['company_name'] = company_name
        extra['company_logo_base64'] = company_logo_base64
        extra['company_code'] = company_code or ''
        return extra



# ==============================================================================
# LOGIN
# ==============================================================================

def LoginView(request, company_code=None):
    """
    Login with automatic database creation on first login.
    Supports both /login/ and /login/<company_code>/
    """
    if not company_code:
        company_code = (
            request.POST.get('company_code')
            or request.GET.get('code')
        )

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        logger.info("[LOGIN ATTEMPT] username=%s company_code=%s", username, company_code)

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect_with_company(request, 'login')

        user = authenticate(
            request,
            username=username,
            password=password,
            company_code=company_code,
        )

        if user is not None:
            try:
                custom_user_id = request.session.get('custom_user_id')
                if custom_user_id:
                    custom_user = (
                        CustomUser.objects.using('default')
                        .select_related('usr_roleid__company', 'company')
                        .get(pk=custom_user_id)
                    )
                else:
                    user_qs = CustomUser.objects.using('default').select_related(
                        'usr_roleid__company', 'company'
                    )
                    if connection.vendor == 'mysql':
                        user_qs = user_qs.extra(
                            where=["BINARY usr_name = %s"],
                            params=[username],
                        )
                    user_qs = user_qs.filter(usr_name=username)
                    if user_qs.count() > 1:
                        messages.error(
                            request,
                            "Multiple users found for this username. Please contact admin."
                        )
                        return redirect_with_company(request, 'login')
                    custom_user = user_qs.first()
                    if not custom_user:
                        raise CustomUser.DoesNotExist

                try:
                    role = custom_user.usr_roleid
                except Exception:
                    role = None

                # Prefer company from role, but gracefully fall back to user.company.
                company = role.company if role and getattr(role, 'company', None) else custom_user.company

                if not company:
                    messages.error(request, "No company assigned to your account")
                    return redirect_with_company(request, 'login')

                # ──────────────────────────────────────────────────────────────
                # FIRST LOGIN: Create database and sync all master data into it
                # ──────────────────────────────────────────────────────────────
                if not company.db_created:
                    logger.info(
                        f"🔄 FIRST LOGIN for {company.name} — creating database..."
                    )

                    db_name = company.db_name

                    try:
                        logger.info(f"[STEP 1] Creating physical database: {db_name}")
                        create_physical_database(db_name)

                        logger.info(f"[STEP 2] Registering database: {db_name}")
                        register_database(db_name)

                        logger.info(f"[STEP 3] Running critical migrations (blocking)")
                        if not run_critical_migrations(db_name):
                            raise Exception("Critical migrations failed")

                        # ── Mark db_created = True BEFORE syncing so that
                        #    _sync_fields_to_company_db() doesn't skip the sync.
                        company.db_created = True
                        company.save(using='default', update_fields=['db_created'])
                        logger.info(f"[STEP 3b] Marked db_created=True in master DB")

                        # ── SYNC: Copy full Company record (including trial
                        #    fields + contact person) from master → company DB.
                        logger.info(
                            f"[STEP 4] Syncing Company record to {db_name}..."
                        )
                        try:
                            sync_company_record(company)
                            logger.info(
                                f"✅ Company record (trial + contact) synced to {db_name}"
                            )
                        except Exception as sync_err:
                            # Log but don't abort login — data can be repaired later
                            logger.error(
                                f"⚠️ Company record sync failed for {db_name}: {sync_err}",
                                exc_info=True,
                            )

                            # ── CREATE DEFAULT WAREHOUSE: Create a default warehouse
                        #    in the company DB with the company's address
                        logger.info(
                            f"[STEP 4b] Creating default warehouse for {db_name}..."
                        )
                        try:
                            from company.signals import create_default_warehouse_for_company
                            if create_default_warehouse_for_company(company):
                                logger.info(
                                    f"✅ Default warehouse created for {db_name}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ Default warehouse creation skipped or failed for {db_name}"
                                )
                        except Exception as warehouse_err:
                            logger.error(
                                f"⚠️ Default warehouse creation failed for {db_name}: {warehouse_err}",
                                exc_info=True,
                            )


                        # ── ASYNC: Full migration + permissions + modules
                        logger.info(
                            f"[STEP 5] Launching async company setup in background..."
                        )
                        run_company_setup_async(
                            db_name, company, role, custom_user, user
                        )

                        logger.info(
                            f"✅ CRITICAL SETUP COMPLETED — "
                            f"async setup running in background"
                        )
                        messages.success(
                            request,
                            "✅ Login successful! Your workspace is being set up in the "
                            "background. You may see a loading message if you navigate "
                            "to other sections."
                        )

                    except Exception as db_error:
                        logger.error(
                            f"❌ Database creation failed: {db_error}", exc_info=True
                        )
                        messages.error(
                            request,
                            "Failed to set up your workspace. Please contact support "
                            "or try again later."
                        )

                        # Rollback db_created flag
                        try:
                            company.db_created = False
                            company.save(using='default', update_fields=['db_created'])
                        except Exception:
                            pass

                        # Try to clean up failed database
                        try:
                            delete_company_database(db_name)
                            logger.info(
                                f"[CLEANUP] Deleted failed database: {db_name}"
                            )
                        except Exception as cleanup_error:
                            logger.error(
                                f"[CLEANUP] Failed to delete database: {cleanup_error}"
                            )

                        return redirect_with_company(request, 'login')

                # ──────────────────────────────────────────────────────────────
                # NORMAL LOGIN (database already exists)
                # ──────────────────────────────────────────────────────────────
                db_name = company.db_name
                register_database(db_name)

                # Sync auth_user in case of password/profile changes
                try:
                    sync_auth_user(user, db_name)
                except Exception as sync_error:
                    logger.warning(f"⚠️ Failed to sync auth_user: {sync_error}")

                login(request, user)

                # Handle "Remember Me" checkbox
                remember_me = request.POST.get('remember_me') == 'on'
                request.session['remember_me'] = remember_me
                
                # Set session timeout based on Remember Me
                if remember_me:
                    # 14 days for Remember Me
                    request.session.set_expiry(1209600)  # 14 days in seconds
                else:
                    # 15 minutes for regular session
                    request.session.set_expiry(900)  # 15 minutes in seconds

                request.session['login_username'] = username
                request.session['usr_roleid'] = role.id if role else None
                request.session['company_id'] = company.id
                request.session['company_db'] = db_name
                request.session['company_code'] = company.company_code
                request.session['is_superadmin'] = False
                request.session.modified = True

                logger.info(
                    f"[LOGIN SUCCESS] User: {username} → "
                    f"Company: {company.name} ({db_name})"
                )

                display_name = (
                    custom_user.usr_fname
                    or getattr(custom_user, 'usr_name', None)
                    or getattr(user, 'username', 'User')
                )
                messages.success(request, f"Welcome back, {display_name}!")

                redirect_kwargs = {}
                code_to_use = company_code or getattr(company, 'company_code', None)
                if code_to_use:
                    redirect_kwargs['company_code'] = code_to_use

                trial_expired = False
                has_valid_license = False
                try:
                    trial_expired = bool(company.check_trial_expired() or getattr(company, 'is_trial_expired', 0) == 1)
                except Exception:
                    trial_expired = bool(getattr(company, 'is_trial_expired', 0) == 1)

                # Fix: Check license in tenant DB (company_db) instead of default DB instance
                try:
                    db_name = company.db_name
                    if db_name:
                        from company_settings.models import LicenseKey
                        has_valid_license = LicenseKey.objects.using(db_name).filter(
                            company_id=company.id,
                            is_active=True,
                            is_license_expired=False
                        ).exists()
                except Exception as e:
                    logger.warning("[LOGIN] Fallback license check failed for %s: %s", company.name, e)
                    has_valid_license = False

                if trial_expired and not has_valid_license:
                    logger.info(
                        "[LOGIN REDIRECT] Trial expired for company=%s code=%s (license_found=%s) -> trial_expired_page",
                        getattr(company, 'name', None),
                        code_to_use,
                        has_valid_license
                    )
                    return redirect_with_company(request, 'trial_expired_page', **redirect_kwargs)


                return redirect_with_company(request, 'index', **redirect_kwargs)

            except CustomUser.DoesNotExist:
                logger.warning(
                    f"[LOGIN WARNING] Custom user not found: {username}"
                )
                messages.error(request, "Username does not exist")
                logout(request)
                return redirect_with_company(request, 'login')

            except Exception as e:
                logger.exception("[LOGIN ERROR] Unexpected exception during login")
                # In DEBUG show the concrete error to aid troubleshooting; otherwise show a generic message
                if getattr(settings, 'DEBUG', False):
                    messages.error(request, f"An error occurred during login: {e}")
                else:
                    messages.error(
                        request,
                        "An error occurred during login. Please try again."
                    )
                return redirect_with_company(request, 'login')

        elif username == "suadmin" and password == "TechL#2024":
            # ── SUPER ADMIN LOGIN ──────────────────────────────────────────
            user, created = DjangoUser.objects.using('default').get_or_create(
                username="suadmin",
                defaults={
                    "first_name": "Super",
                    "last_name": "Admin",
                    "email": "admin@example.com",
                    "is_superuser": True,
                    "is_staff": True,
                },
            )
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save(using='default')
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

            # Handle "Remember Me" for super admin
            remember_me = request.POST.get('remember_me') == 'on'
            request.session['remember_me'] = remember_me
            
            # Set session timeout based on Remember Me
            if remember_me:
                # 14 days for Remember Me
                request.session.set_expiry(1209600)  # 14 days in seconds
            else:
                # 15 minutes for regular session
                request.session.set_expiry(900)  # 15 minutes in seconds

            companies = Company.objects.using('default').filter(db_created=True)
            for co in companies:
                if co.db_name:
                    try:
                        register_database(co.db_name)
                        sync_auth_user(user, co.db_name)
                        logger.info(f"✅ suadmin synced to {co.db_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ suadmin sync failed for {co.db_name}: {e}")

            request.session['login_username'] = "suadmin"
            request.session['company_id'] = None
            request.session['company_db'] = 'default'
            request.session['is_superadmin'] = True
            request.session.modified = True

            messages.success(request, "Logged in as Super Admin")
            logger.info("✅ SUPER ADMIN LOGIN SUCCESS")

            if not Company.objects.using('default').exists():
                return redirect_with_company(request, 'company_registration')

            return redirect_with_company(request, 'index')

        else:
            if request.session.pop('login_ambiguous', False):
                messages.error(
                    request,
                    'This username exists in multiple companies. Use your company login URL.'
                )
            else:
                user_qs = CustomUser.objects.using('default')
                if connections['default'].vendor == 'mysql':
                    user_qs = user_qs.extra(
                        where=["BINARY usr_name = %s"],
                        params=[username],
                    )
                else:
                    user_qs = user_qs.filter(usr_name=username)

                matched_users = list(user_qs[:2])
                if not matched_users:
                    messages.error(request, 'Username does not exist')
                elif len(matched_users) > 1:
                    messages.error(
                        request,
                        'This username exists in multiple companies. Use your company login URL.'
                    )
                elif not check_password(password, matched_users[0].usr_pwd):
                    messages.error(request, 'Incorrect password')
                else:
                    messages.error(request, 'Unable to login with this account')
            logger.warning(
                f"[LOGIN FAILED] Invalid credentials for username: {username}"
            )

    context = {'company_code': company_code}
    return render(request, 'website/login.html', context)


# ==============================================================================
# DASHBOARD
# ==============================================================================

@login_required(login_url='/login/')
def DashboardView(request):
    company_id = request.session.get('company_id')
    company_db = request.session.get('company_db', 'default')

    company = Company.objects.using(company_db).filter(pk=company_id).first()
    
    show_setup_checklist = False
    if company and not company.setup_checklist_shown:
        show_setup_checklist = True
        # Mark it shown so it never appears again
        Company.objects.using(company_db).filter(pk=company_id).update(
            setup_checklist_shown=True
        )
        # Sync to master DB too
        Company.objects.using('default').filter(pk=company_id).update(
            setup_checklist_shown=True
        )

    # Check what's already configured so you can tick items
    has_taxes = Tax.objects.using(company_db).exists()
    has_email_config = EmailTemplateStyle.objects.using(company_db).filter(
        is_default=True
    ).exists()

    context = {
        'company_id': company_id,
        'company_db': company_db,
        'show_setup_checklist': show_setup_checklist,
        'has_taxes': has_taxes,
        'has_email_config': has_email_config,
    }
    return render(request, 'website/index.html', context)

# ==============================================================================
# LOGOUT
# ==============================================================================

def LogoutView(request):
    """Logout"""
    username = request.session.get('login_username', 'Unknown')
    logout(request)
    logger.info(f"[LOGOUT] User logged out: {username}")
    messages.success(request, "You have been logged out successfully")
    return redirect_with_company(request, 'login')


# ==============================================================================
# SIGNUP
# ==============================================================================

def Signup(request):
    """
    Simplified signup — NO database creation at this stage.

    Creates company + user records in master DB only, starts the trial
    clock, and emails the user their unique login URL.
    The physical company database is created on first login.
    """

    # AJAX EMAIL CHECK
    if (
        request.method == "GET"
        and request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ):
        email = request.GET.get("email", "").strip()
        if email:
            try:
                exists = CustomUser.objects.using('default').filter(
                    usr_mail=email
                ).exists()
            except Exception:
                exists = False
            return JsonResponse({"exists": exists})
        return JsonResponse({"exists": False})

    if request.method == "GET":
        return render(request, "website/signup.html", {'countries': countries})

    # ── POST ──────────────────────────────────────────────────────────────────
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        company_name = request.POST.get("company_name", "").strip()
        username     = request.POST.get("username", "").strip()
        email        = request.POST.get("email", "").strip()
        phone        = request.POST.get("phone", "").strip()
        country_code = request.POST.get("country_code", "").strip()
        password     = request.POST.get("password", "").strip()
        country      = request.POST.get("country", "").strip()
        state        = request.POST.get("state", "").strip()

        # Validation
        if not all([company_name, username, email, phone, password, country, state]):
            error_msg = "Please fill all required fields"
            logger.warning("[SIGNUP VALIDATION] Missing required fields")
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg})
            messages.error(request, error_msg)
            return redirect_with_company(request, "signup")

        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            error_msg = (
                "Username must be 3-20 characters "
                "(letters, numbers, underscore only)"
            )
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg})
            messages.error(request, error_msg)
            return redirect_with_company(request, "signup")

        # Server-side duplicate guard: do not rely only on frontend AJAX.
        username_exists = (
            CustomUser.objects.using('default').filter(usr_name__iexact=username).exists()
            or DjangoUser.objects.using('default').filter(username__iexact=username).exists()
        )
        if username_exists:
            error_msg = "This username is already taken. Please choose a different one."
            logger.warning("[SIGNUP VALIDATION] Duplicate username rejected: %s", username)
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg})
            messages.error(request, error_msg)
            return redirect_with_company(request, "signup")

        company     = None
        db_name     = None
        django_user = None

        try:
            # ── STEP 1: Create Company in master DB
            # We do this in two sub-steps:
            #   1a. Save to get the auto-generated PK (needed for code/db_name generation)
            #   1b. Update code + db_name + re-confirm contact fields in one update()
            #       call so nothing is overwritten by the router or a stale instance.
            with transaction.atomic(using='default'):
                contact_phone = f"{country_code}{phone}".strip()

                # 1a — initial save to get PK
                company = Company(
                    name=company_name,
                    email=email,
                    phone=contact_phone,
                    state=state,
                    setup_complete=False,
                    db_created=False,
                    first_login_completed=False,
                )
                company.country = country
                company.save(using='default')

                # 1b — generate code + db_name now that we have a PK,
                #       then write ALL three fields in a single .update()
                #       to guarantee they land in master DB together.
                comp_code = generate_company_code(company_name, company.id)
                db_name   = generate_db_name(company_name, company.id, company_code=comp_code)

                Company.objects.using('default').filter(pk=company.pk).update(
                    company_code=comp_code,
                    db_name=db_name,
                    # Re-assert contact details here so even if the first save()
                    # was silently routed elsewhere they are guaranteed in master.
                    email=email,
                    phone=contact_phone,
                )

                # Keep the in-memory instance in sync
                company.company_code = comp_code
                company.db_name = db_name
                company.email = email
                company.phone = contact_phone

                logger.info(
                    f"✅ [STEP 1] Company created in master DB: "
                    f"{company.name} (Code: {comp_code}, DB will be: {db_name})"
                )

            # ── STEP 2: Create Admin Role in master DB
            with transaction.atomic(using='default'):
                admin_role = Role.objects.using('default').create(
                    role_name="Admin",
                    company=company,
                    description="Administrator role with full access"
                )
                logger.info("✅ [STEP 2] Admin role created in master DB")

            # ── STEP 3: Create CustomUser in master DB
            with transaction.atomic(using='default'):
                master_user = CustomUser.objects.using('default').create(
                    usr_name=username,
                    usr_fname=company_name,
                    usr_mail=email,
                    usr_phn=contact_phone,
                    usr_pwd=make_password(password),
                    usr_roleid=admin_role,
                    company=company,
                )
                logger.info(
                    f"✅ [STEP 3] CustomUser created in master DB: {username}"
                )

            # ── STEP 4: Create Django auth_user in master DB
            with transaction.atomic(using='default'):
                django_user, _ = DjangoUser.objects.using('default').update_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': company_name,
                        'is_active': True,
                    },
                )
                django_user.set_password(password)
                django_user.save(using='default')
                logger.info(
                    f"✅ [STEP 4] auth_user created in master DB: {username}"
                )

            # ── STEP 5: Start trial (saved to master DB only at this point)
            # db_created is still False here, so _sync_fields_to_company_db()
            # inside activate_trial() / start_trial() will be a no-op.
            # The trial fields will be synced to the company DB in Step 4 of
            # the first-login flow via sync_company_record().
            company.activate_trial()
            company.start_trial()
            logger.info(
                f"✅ [STEP 5] Trial started in master DB for {company.name} — "
                f"expires {company.trial_expires_at}"
            )

            # ── STEP 6: Send registration email
            email_sent = send_registration_email(company, email, username)
            if not email_sent:
                logger.warning(
                    "⚠️ Registration email failed but signup succeeded"
                )

            success_msg = (
                f"Registration successful! "
                f"Please check your email at {email} for your unique login link. "
                f"Your company code is: {comp_code}"
            )

            logger.info(
                f"✅ SIGNUP COMPLETED for {username} — "
                f"database creation deferred to first login"
            )

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": success_msg,
                    "redirect_url": reverse("login"),
                })

            messages.success(request, success_msg)
            return redirect_with_company(request, "login")

        except Exception as e:
            logger.error(f"❌ SIGNUP ERROR: {str(e)}", exc_info=True)

            # Cleanup master DB records on failure
            try:
                if company:
                    CustomUser.objects.using('default').filter(
                        usr_roleid__company=company
                    ).delete()
                    Role.objects.using('default').filter(company=company).delete()
                    if django_user:
                        DjangoUser.objects.using('default').filter(
                            id=django_user.id
                        ).delete()
                    company.delete(using='default')
                    logger.info("[CLEANUP] Deleted company records from master DB")
            except Exception as cleanup_error:
                logger.error(f"[CLEANUP] Cleanup failed: {cleanup_error}")

            error_msg = f"Signup failed: {str(e)}"

            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg})

            messages.error(request, error_msg)
            return redirect_with_company(request, "signup")

    return render(request, "website/signup.html", {"countries": countries})


# ==============================================================================
# UTILITY ENDPOINTS
# ==============================================================================

def check_email_exists(request):
    """API endpoint to check if email exists"""
    if request.method == "GET":
        email = request.GET.get("email", "").strip()
        if email:
            exists = CustomUser.objects.using('default').filter(
                usr_mail=email
            ).exists()
            return JsonResponse({"exists": exists})
        return JsonResponse({"exists": False})
    return JsonResponse({"error": "Invalid request"}, status=400)


def check_username_exists(request):
    """API endpoint to check if username exists"""
    if request.method == "GET":
        username = request.GET.get("username", "").strip()
        if username:
            exists = (
                CustomUser.objects.using('default').filter(usr_name__iexact=username).exists()
                or DjangoUser.objects.using('default').filter(username__iexact=username).exists()
            )
            return JsonResponse({"exists": exists})
        return JsonResponse({"exists": False})
    return JsonResponse({"error": "Invalid request"}, status=400)


def migration_status(request):
    """Check migration status for a company database"""
    db_name = request.GET.get('db_name', '').strip()
    if not db_name:
        return JsonResponse({"error": "db_name required"}, status=400)

    status = get_migration_status(db_name)
    return JsonResponse(status)
