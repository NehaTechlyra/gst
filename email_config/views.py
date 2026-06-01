from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import EmailConfiguration
from email_templates.constants import TEMPLATE_NAME_CHOICES
from .permissions import (
    can_view_email_config, can_create_email_config,
    can_edit_email_config, can_delete_email_config
)   


def _redirect_to_settings_email_tab(request):
    settings_url = get_company_redirect_url(request, 'settings_page')
    return redirect(f"{settings_url}?tab=email")


# ─────────────────────────────────────────────
# LIST VIEW
# ─────────────────────────────────────────────

@login_required
def email_config_list(request):
    # Permission check - require view access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_email_config(request.user)):
            messages.error(request, 'You do not have permission to view Email Configuration.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view Email Configuration.')
        return redirect_with_company('home')
    
    items = EmailConfiguration.objects.filter(status=True).order_by('id')
    return render(request, 'email_config/list.html', {
        'items': items,
        'templates': TEMPLATE_NAME_CHOICES
    })


# ─────────────────────────────────────────────
# CREATE VIEW
# ─────────────────────────────────────────────

@login_required
def email_config_create(request):
    # Permission check - require create access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_email_config(request.user)):
            messages.error(request, 'You do not have permission to create Email Configuration.')
            return _redirect_to_settings_email_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to create Email Configuration.')
        return _redirect_to_settings_email_tab(request)
    
    next_target = request.GET.get('next') or request.POST.get('next')

    default_email = EmailConfiguration.objects.filter(is_default=True, status=True).first()

    # Template choices (not model objects)
    templates = TEMPLATE_NAME_CHOICES

    if request.method == 'POST':
        host = request.POST.get('host')
        port = request.POST.get('port') or 587
        use_tls = request.POST.get('use_tls') == 'on'
        host_user = request.POST.get('host_user')
        host_password = request.POST.get('host_password')
        default_from_email = request.POST.get('default_from_email') or (
            default_email.default_from_email if default_email else ''
        )
        usage_list = request.POST.getlist('usage_types')  # list of template names
        status = request.POST.get('status') == 'on'

        if host and host_user:
            obj = EmailConfiguration.objects.create(
                host=host,
                port=port,
                use_tls=use_tls,
                host_user=host_user,
                host_password=host_password,
                default_from_email=default_from_email,
                status=status,
                created_by=request.user,
                updated_by=request.user,
                usage_types=usage_list   # DIRECT ASSIGN
            )

            # Set default email config
            if request.POST.get('is_default') == 'on':
                EmailConfiguration.objects.update(is_default=False)
                obj.is_default = True
                obj.save(update_fields=['is_default'])

            messages.success(request, "Email configuration added successfully!")

            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                return redirect_with_company(reverse('settings_page') + next_target)

            return _redirect_to_settings_email_tab(request)

    return render(request, 'email_config/create.html', {
        'default_email': default_email,
        'templates': templates
    })


# ─────────────────────────────────────────────
# EDIT VIEW
# ─────────────────────────────────────────────

@login_required
def email_config_edit(request, pk):
    # Permission check - require edit access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_email_config(request.user)):
            messages.error(request, 'You do not have permission to edit Email Configuration.')
            return _redirect_to_settings_email_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to edit Email Configuration.')
        return _redirect_to_settings_email_tab(request)
    
    next_target = request.GET.get('next') or request.POST.get('next')
    obj = get_object_or_404(EmailConfiguration, pk=pk)
    default_email = EmailConfiguration.objects.filter(is_default=True, status=True).first()

    templates = TEMPLATE_NAME_CHOICES

    if request.method == 'POST':
        obj.host = request.POST.get('host')
        obj.port = request.POST.get('port') or 587
        obj.use_tls = request.POST.get('use_tls') == 'on'
        obj.host_user = request.POST.get('host_user')
        obj.host_password = request.POST.get('host_password')
        obj.default_from_email = request.POST.get('default_from_email') or (
            default_email.default_from_email if default_email else ''
        )
        obj.status = request.POST.get('status') == 'on'
        obj.updated_by = request.user

        # Update usage types (list of strings)
        usage_list = request.POST.getlist('usage_types')
        obj.usage_types = usage_list

        obj.save()

        # Handle default selection
        if request.POST.get('is_default') == 'on':
            EmailConfiguration.objects.update(is_default=False)
            obj.is_default = True
            obj.save(update_fields=['is_default'])

        messages.success(request, "Email configuration updated successfully!")

        if next_target:
            if not next_target.startswith('#'):
                next_target = '#' + next_target
            return redirect_with_company(reverse('settings_page') + next_target)

        return _redirect_to_settings_email_tab(request)

    return render(request, 'email_config/create.html', {
        'obj': obj,
        'next': next_target,
        'default_email': default_email,
        'templates': templates
    })


# ─────────────────────────────────────────────
# DEACTIVATE
# ─────────────────────────────────────────────

@login_required
def email_config_deactivate(request, pk):
    # Permission check - require delete access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_email_config(request.user)):
            messages.error(request, 'You do not have permission to delete Email Configuration.')
            return _redirect_to_settings_email_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to delete Email Configuration.')
        return _redirect_to_settings_email_tab(request)

    try:
        obj = EmailConfiguration.objects.get(pk=pk)
        obj.status = False
        obj.save(update_fields=['status'])
        messages.success(request, "Email configuration deleted successfully!")
    except EmailConfiguration.DoesNotExist:
        messages.error(request, "Email configuration not found.")

    return _redirect_to_settings_email_tab(request)


# ─────────────────────────────────────────────
# SET DEFAULT
# ─────────────────────────────────────────────
def email_set_default(request, id):
    obj = get_object_or_404(EmailConfiguration, id=id)
    EmailConfiguration.objects.update(is_default=False)
    obj.is_default = True
    obj.save()
    messages.success(request, "Default email configuration updated.")
    return _redirect_to_settings_email_tab(request)
