# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib import messages
# from django.db import transaction
# from .models import SMSTemplateOption
# from .constants import SMS_TEMPLATE_NAME_CHOICES


# # ---------------- LIST VIEW ---------------- #
# def sms_template_list(request):
#     """
#     Fixed version - groups SMS templates by template_name
#     Returns a dictionary with template_name as key and options as value
#     """
#     grouped_sms_templates = {}

#     for value, label in SMS_TEMPLATE_NAME_CHOICES:
#         options = SMSTemplateOption.objects.filter(
#             template_name=value,
#             status=True
#         ).order_by("-is_default", "style")

#         # Use the value (internal name) as the key
#         grouped_sms_templates[value] = options

#     return render(request, "sms_templates/list.html", {
#         "grouped_sms_templates": grouped_sms_templates,
#         "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
#     })


# # ---------------- CREATE VIEW ---------------- #
# def sms_template_create(request):

#     if request.method == "POST":

#         template_name = request.POST.get("template_name", "").strip()
#         style = request.POST.get("style", "").strip()
#         content = request.POST.get("content", "").strip()
#         is_default = bool(request.POST.get("is_default"))
#         status = bool(request.POST.get("status"))

#         with transaction.atomic():

#             option = SMSTemplateOption.objects.create(
#                 template_name=template_name,
#                 style=style,
#                 content=content,
#                 is_default=is_default,
#                 status=status,
#             )

#             # Only one default per template_name
#             if is_default:
#                 SMSTemplateOption.objects.filter(
#                     template_name=template_name
#                 ).exclude(id=option.id).update(is_default=False)

#         messages.success(request, "SMS Template Option Created Successfully")
#         return redirect("sms_template_list")

#     return render(request, "sms_templates/create.html", {
#         "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
#     })


# # ---------------- EDIT VIEW ---------------- #
# def sms_template_edit(request, pk):

#     option = get_object_or_404(SMSTemplateOption, pk=pk)

#     if request.method == "POST":

#         option.template_name = request.POST.get("template_name", "").strip()
#         option.style = request.POST.get("style", "").strip()
#         option.content = request.POST.get("content", "").strip()
#         option.status = bool(request.POST.get("status"))
#         option.is_default = bool(request.POST.get("is_default"))
#         option.save()

#         # Only one default per template_name
#         if option.is_default:
#             SMSTemplateOption.objects.filter(
#                 template_name=option.template_name
#             ).exclude(id=option.id).update(is_default=False)

#         messages.success(request, "SMS Template Option Updated Successfully")
#         return redirect("sms_template_list")

#     return render(request, "sms_templates/create.html", {
#         "obj": option,
#         "selected_name": option.template_name,
#         "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
#     })


# # ---------------- SET DEFAULT ---------------- #
# def sms_template_set_default(request, pk):

#     option = get_object_or_404(SMSTemplateOption, pk=pk)

#     SMSTemplateOption.objects.filter(
#         template_name=option.template_name
#     ).update(is_default=False)

#     option.is_default = True
#     option.status = True
#     option.save(update_fields=["is_default", "status"])

#     messages.success(request, "Default SMS Template Updated Successfully")
#     return redirect("sms_template_list")


# # ---------------- DELETE OPTION ---------------- #
# def sms_template_delete(request, pk):

#     option = get_object_or_404(SMSTemplateOption, pk=pk)
#     option.delete()

#     messages.success(request, "SMS Template Deleted Successfully")
#     return redirect("sms_template_list")




from django.shortcuts import render, get_object_or_404, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import SMSTemplateOption
from .constants import SMS_TEMPLATE_NAME_CHOICES, HARDCODED_SMS_TEMPLATES
from .permissions import (
    can_view_sms_templates, can_create_sms_templates,
    can_edit_sms_templates, can_delete_sms_templates
)


def _redirect_to_settings_sms_template_tab(request):
    settings_url = get_company_redirect_url(request, 'settings_page')
    return redirect(f"{settings_url}?tab=sms_template")


# ---------------- LIST VIEW ---------------- #

@login_required
def sms_template_list(request):
    """
    Merges hardcoded templates with database templates
    Hardcoded templates are marked with is_hardcoded=True
    """
    # Permission check - require view access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_sms_templates(request.user)):
            messages.error(request, 'You do not have permission to view SMS Templates.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view SMS Templates.')
        return redirect_with_company('home')
    
    grouped_sms_templates = {}

    for value, label in SMS_TEMPLATE_NAME_CHOICES:
        # Start with hardcoded templates
        hardcoded_templates = HARDCODED_SMS_TEMPLATES.get(value, [])
        
        # Convert hardcoded templates to a unified format
        all_templates = []
        
        # Check if any hardcoded template is set as default in DB
        default_hardcoded_style = None
        default_db_record = SMSTemplateOption.objects.filter(
            template_name=value,
            is_default=True,
            is_hardcoded=True,
            status=True
        ).first()
        
        if default_db_record:
            default_hardcoded_style = default_db_record.style
        
        # Add hardcoded templates
        for template in hardcoded_templates:
            all_templates.append({
                "id": None,  # No database ID for hardcoded
                "style": template["style"],
                "content": template["content"],
                "is_hardcoded": True,
                "is_default": template["style"] == default_hardcoded_style,
                "status": True,
            })
        
        # Get custom templates from database
        custom_templates = SMSTemplateOption.objects.filter(
            template_name=value,
            is_hardcoded=False,
            status=True
        ).order_by("-is_default", "style")
        
        # Add custom templates
        for template in custom_templates:
            all_templates.append({
                "id": template.id,
                "style": template.style,
                "content": template.content,
                "is_hardcoded": False,
                "is_default": template.is_default,
                "status": template.status,
            })
        
        # If no default is set, mark the first template as default
        if all_templates and not any(t["is_default"] for t in all_templates):
            all_templates[0]["is_default"] = True
        
        grouped_sms_templates[value] = all_templates

    return render(request, "sms_templates/list.html", {
        "grouped_sms_templates": grouped_sms_templates,
        "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
    })


# ---------------- CREATE VIEW ---------------- #

@login_required
def sms_template_create(request):
    # Permission check - require create access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_sms_templates(request.user)):
            messages.error(request, 'You do not have permission to create SMS Templates.')
            return _redirect_to_settings_sms_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to create SMS Templates.')
        return _redirect_to_settings_sms_template_tab(request)
    
    if request.method == "POST":
        template_name = request.POST.get("template_name", "").strip()
        style = request.POST.get("style", "").strip()
        content = request.POST.get("content", "").strip()
        is_default = bool(request.POST.get("is_default"))
        status = bool(request.POST.get("status"))

        with transaction.atomic():
            option = SMSTemplateOption.objects.create(
                template_name=template_name,
                style=style,
                content=content,
                is_default=is_default,
                status=status,
                is_hardcoded=False,  # Custom templates are never hardcoded
            )

            # Only one default per template_name
            if is_default:
                SMSTemplateOption.objects.filter(
                    template_name=template_name
                ).exclude(id=option.id).update(is_default=False)

        messages.success(request, "SMS Template Option Created Successfully")
        return _redirect_to_settings_sms_template_tab(request)

    return render(request, "sms_templates/create.html", {
        "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
    })


# ---------------- EDIT VIEW ---------------- #

@login_required
def sms_template_edit(request, pk):
    # Permission check - require edit access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_sms_templates(request.user)):
            messages.error(request, 'You do not have permission to edit SMS Templates.')
            return _redirect_to_settings_sms_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to edit SMS Templates.')
        return _redirect_to_settings_sms_template_tab(request)
    
    option = get_object_or_404(SMSTemplateOption, pk=pk)

    # Prevent editing hardcoded templates
    if option.is_hardcoded:
        messages.error(request, "Cannot edit hardcoded templates")
        return _redirect_to_settings_sms_template_tab(request)

    if request.method == "POST":
        option.template_name = request.POST.get("template_name", "").strip()
        option.style = request.POST.get("style", "").strip()
        option.content = request.POST.get("content", "").strip()
        option.status = bool(request.POST.get("status"))
        option.is_default = bool(request.POST.get("is_default"))
        option.save()

        # Only one default per template_name
        if option.is_default:
            SMSTemplateOption.objects.filter(
                template_name=option.template_name
            ).exclude(id=option.id).update(is_default=False)

        messages.success(request, "SMS Template Option Updated Successfully")
        return _redirect_to_settings_sms_template_tab(request)

    return render(request, "sms_templates/create.html", {
        "obj": option,
        "selected_name": option.template_name,
        "SMS_TEMPLATE_NAME_CHOICES": SMS_TEMPLATE_NAME_CHOICES,
    })


# ---------------- SET DEFAULT ---------------- #
def sms_template_set_default(request, template_name, style):
    """
    Handle setting default for both hardcoded and custom templates
    template_name: e.g., "Document Expiry Reminder"
    style: e.g., "Professional"
    """
    # Check if it's a hardcoded template
    hardcoded_templates = HARDCODED_SMS_TEMPLATES.get(template_name, [])
    is_hardcoded = any(t["style"] == style for t in hardcoded_templates)

    with transaction.atomic():
        # Clear all defaults for this template_name
        SMSTemplateOption.objects.filter(template_name=template_name).update(is_default=False)

        if is_hardcoded:
            # Create or update a DB record for the hardcoded template to mark it as default
            SMSTemplateOption.objects.update_or_create(
                template_name=template_name,
                style=style,
                is_hardcoded=True,
                defaults={
                    "content": next(t["content"] for t in hardcoded_templates if t["style"] == style),
                    "is_default": True,
                    "status": True,
                }
            )
        else:
            # It's a custom template
            option = get_object_or_404(SMSTemplateOption, template_name=template_name, style=style, is_hardcoded=False)
            option.is_default = True
            option.status = True
            option.save(update_fields=["is_default", "status"])

    messages.success(request, "Default SMS Template Updated Successfully")
    return _redirect_to_settings_sms_template_tab(request)


# ---------------- DELETE OPTION ---------------- #

@login_required
def sms_template_delete(request, pk):
    # Permission check - require delete access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_sms_templates(request.user)):
            messages.error(request, 'You do not have permission to delete SMS Templates.')
            return _redirect_to_settings_sms_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to delete SMS Templates.')
        return _redirect_to_settings_sms_template_tab(request)
    
    option = get_object_or_404(SMSTemplateOption, pk=pk)

    # Prevent deleting hardcoded templates
    if option.is_hardcoded:
        messages.error(request, "Cannot delete hardcoded templates")
        return _redirect_to_settings_sms_template_tab(request)

    option.delete()
    messages.success(request, "SMS Template Deleted Successfully")
    return _redirect_to_settings_sms_template_tab(request)
