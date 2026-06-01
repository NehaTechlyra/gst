from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from html import unescape as html_unescape
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import os
from django.conf import settings
from django.utils.text import get_valid_filename

from .models import EmailTemplateStyle
from email_templates.constants import TEMPLATE_NAME_CHOICES, HARDCODED_EMAIL_TEMPLATES
from .permissions import (
    can_view_email_templates, can_create_email_templates,
    can_edit_email_templates, can_delete_email_templates
)


def _redirect_to_settings_email_template_tab(request):
    settings_url = get_company_redirect_url(request, 'settings_page')
    return redirect(f"{settings_url}?tab=email_template")

# ===================================================================
#                           LIST VIEW
# ===================================================================

@login_required
def email_template_list(request):
    """
    Merges hardcoded email templates with database templates
    """
    # Permission check - require view access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_email_templates(request.user)):
            messages.error(request, 'You do not have permission to view Email Templates.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view Email Templates.')
        return redirect_with_company('home')
    
    template_groups = {}

    for value, label in TEMPLATE_NAME_CHOICES:
        # Start with hardcoded templates
        hardcoded_templates = HARDCODED_EMAIL_TEMPLATES.get(value, [])
        
        # Convert hardcoded templates to a unified format
        all_templates = []
        
        # Check if any hardcoded template is set as default in DB
        default_hardcoded_style = None
        default_db_record = EmailTemplateStyle.objects.filter(
            template_name=value,
            is_default=True,
            is_hardcoded=True,
            status=True
        ).first()
        
        if default_db_record:
            default_hardcoded_style = default_db_record.style
        
        # Add hardcoded templates
        for template in hardcoded_templates:
            body_html = template["body"]
            # If the template defines attach_pdf, insert a visible attach-option block
            if template.get("attach_pdf"):
                attach_html = (
                    "\n            <div class=\"attach-option\" style=\"padding:12px 20px; background:#fff; border:1px dashed #ddd; margin:18px 0;\">\n                "
                    "<label style=\"font-weight:600;\">Attach PDF: [[attach_pdf:true]]</label>\n            </div>\n"
                )
                # try to insert before the footer div; fallback to appending
                if "</div>\n        <div class=\"footer\">" in body_html:
                    body_html = body_html.replace(
                        "</div>\n        <div class=\"footer\">",
                        "</div>" + attach_html + "        <div class=\"footer\">",
                    )
                else:
                    body_html = body_html + attach_html

            all_templates.append({
                "id": None,  # No database ID for hardcoded
                "style": template["style"],
                "subject": template["subject"],
                "body": body_html,
                "is_hardcoded": True,
                "is_default": template["style"] == default_hardcoded_style,
                "status": True,
            })
        
        # Get custom templates from database
        custom_templates = EmailTemplateStyle.objects.filter(
            template_name=value,
            is_hardcoded=False,
            status=True
        ).order_by("-is_default", "style")
        
        # Add custom templates
        for template in custom_templates:
            all_templates.append({
                "id": template.id,
                "style": template.style,
                "subject": template.subject,
                "body": template.body,
                "is_hardcoded": False,
                "is_default": template.is_default,
                "status": template.status,
            })
        
        # If no default is set, mark the first template as default
        if all_templates and not any(t["is_default"] for t in all_templates):
            all_templates[0]["is_default"] = True
        
        template_groups[value] = all_templates

    return render(request, "email_templates/list.html", {
        "template_groups": template_groups,
        "TEMPLATE_NAME_CHOICES": TEMPLATE_NAME_CHOICES,
    })


# ===================================================================
#                          CREATE VIEW
# ===================================================================

@login_required
def email_template_create(request):
    # Permission check - require create access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_email_templates(request.user)):
            messages.error(request, 'You do not have permission to create Email Templates.')
            return _redirect_to_settings_email_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to create Email Templates.')
        return _redirect_to_settings_email_template_tab(request)

    if request.method == "POST":

        name = request.POST.get("template_name", "").strip()
        style = request.POST.get("style", "").strip()
        subject = request.POST.get("subject", "")
        body = html_unescape(request.POST.get("body", "")).strip()
        is_default = bool(request.POST.get("is_default"))
        status = bool(request.POST.get("status"))

        with transaction.atomic():

            # Create template style
            style_obj = EmailTemplateStyle.objects.create(
                template_name=name,
                style=style,
                subject=subject,
                body=body,
                is_default=is_default,
                status=status,
                is_hardcoded=False,  # Custom templates are never hardcoded
                created_by=request.user,
                updated_by=request.user
            )

            # Only one default per template
            if is_default:
                EmailTemplateStyle.objects.filter(
                    template_name=name
                ).exclude(id=style_obj.id).update(is_default=False)

        messages.success(request, "Template Style Created Successfully")
        return _redirect_to_settings_email_template_tab(request)

    return render(request, "email_templates/create.html", {
        "TEMPLATE_NAME_CHOICES": TEMPLATE_NAME_CHOICES
    })


# ===================================================================
#                          EDIT VIEW
# ===================================================================

@login_required
def email_template_edit(request, pk):
    # Permission check - require edit access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_email_templates(request.user)):
            messages.error(request, 'You do not have permission to edit Email Templates.')
            return _redirect_to_settings_email_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to edit Email Templates.')
        return _redirect_to_settings_email_template_tab(request)

    style_obj = get_object_or_404(EmailTemplateStyle, pk=pk)

    # Prevent editing hardcoded templates
    if style_obj.is_hardcoded:
        messages.error(request, "Cannot edit hardcoded templates")
        return _redirect_to_settings_email_template_tab(request)

    if request.method == "POST":

        style_obj.template_name = request.POST.get("template_name", "").strip()
        style_obj.style = request.POST.get("style", "").strip()
        style_obj.subject = request.POST.get("subject", "")
        style_obj.body = request.POST.get("body", "")
        style_obj.status = bool(request.POST.get("status"))
        style_obj.is_default = bool(request.POST.get("is_default"))
        style_obj.updated_by = request.user
        style_obj.save()

        # Only one default per template_name
        if style_obj.is_default:
            EmailTemplateStyle.objects.filter(
                template_name=style_obj.template_name
            ).exclude(id=style_obj.id).update(is_default=False)

        messages.success(request, "Template Style Updated Successfully")
        return _redirect_to_settings_email_template_tab(request)

    return render(request, "email_templates/create.html", {
        "obj": style_obj,
        "TEMPLATE_NAME_CHOICES": TEMPLATE_NAME_CHOICES,
    })


# ===================================================================
#              SET DEFAULT TEMPLATE STYLE (ONE PER NAME)
# ===================================================================
def set_default_email_template(request, template_name, style):
    """
    Handle setting default for both hardcoded and custom templates
    """
    # Check if it's a hardcoded template
    hardcoded_templates = HARDCODED_EMAIL_TEMPLATES.get(template_name, [])
    is_hardcoded = any(t["style"] == style for t in hardcoded_templates)

    with transaction.atomic():
        # Clear all defaults for this template_name
        EmailTemplateStyle.objects.filter(template_name=template_name).update(is_default=False)

        if is_hardcoded:
            # Find the hardcoded template
            hardcoded_template = next(t for t in hardcoded_templates if t["style"] == style)
            
            # Create or update a DB record for the hardcoded template to mark it as default
            EmailTemplateStyle.objects.update_or_create(
                template_name=template_name,
                style=style,
                is_hardcoded=True,
                defaults={
                    "subject": hardcoded_template["subject"],
                    "body": hardcoded_template["body"],
                    "is_default": True,
                    "status": True,
                }
            )
        else:
            # It's a custom template
            obj = get_object_or_404(EmailTemplateStyle, template_name=template_name, style=style, is_hardcoded=False)
            obj.is_default = True
            obj.status = True
            obj.save(update_fields=["is_default", "status"])

    messages.success(request, "Default Template Updated Successfully")
    return _redirect_to_settings_email_template_tab(request)


# ===================================================================
#                           DELETE VIEW
# ===================================================================

@login_required
def email_template_delete(request, pk):
    # Permission check - require delete access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_email_templates(request.user)):
            messages.error(request, 'You do not have permission to delete Email Templates.')
            return _redirect_to_settings_email_template_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to delete Email Templates.')
        return _redirect_to_settings_email_template_tab(request)

    obj = get_object_or_404(EmailTemplateStyle, pk=pk)

    # Prevent deleting hardcoded templates
    if obj.is_hardcoded:
        messages.error(request, "Cannot delete hardcoded templates")
        return _redirect_to_settings_email_template_tab(request)

    obj.delete()
    messages.success(request, "Template Deleted Successfully")
    return _redirect_to_settings_email_template_tab(request)


# ===================================================================
#                   SUMMERNOTE UPLOAD HANDLER
# ===================================================================
@csrf_exempt
def summernote_upload(request):

    if request.method == 'POST':

        upload_file = (
            request.FILES.get('file') or
            request.FILES.get('image') or
            request.FILES.get('video')
        )

        if not upload_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        filename = get_valid_filename(upload_file.name)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'summernote_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        # Avoid filename collisions
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base}_{counter}{ext}"
            file_path = os.path.join(upload_dir, filename)
            counter += 1

        # Save the file
        with open(file_path, 'wb+') as f:
            for chunk in upload_file.chunks():
                f.write(chunk)

        file_url = settings.MEDIA_URL + 'summernote_uploads/' + filename
        return JsonResponse(file_url, safe=False)

    return JsonResponse({'error': 'Invalid request'}, status=400)


# ===================================================================
#                    HELPER FUNCTION
# ===================================================================
def get_default_email_template(template_name):
    """
    Get the default email template for a given template_name.
    First checks DB for default (custom or hardcoded marker),
    then falls back to first hardcoded template if no default is set.
    
    Returns dict with 'subject', 'body', and 'attach_pdf' or None.
    """
    # Check if there's a default in the database
    db_template = EmailTemplateStyle.objects.filter(
        template_name=template_name,
        is_default=True,
        status=True
    ).first()
    
    if db_template:
        return {
            "subject": db_template.subject,
            "body": db_template.body,
            "attach_pdf": True  # DB templates always have attach_pdf support
        }
    
    # Fall back to first hardcoded template
    hardcoded_templates = HARDCODED_EMAIL_TEMPLATES.get(template_name, [])
    if hardcoded_templates:
        hardcoded = hardcoded_templates[0]
        return {
            "subject": hardcoded["subject"],
            "body": hardcoded["body"],
            "attach_pdf": hardcoded.get("attach_pdf", True)
        }
    
    return None
