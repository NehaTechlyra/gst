# from django.shortcuts import render, redirect, get_object_or_404
# from django.urls import reverse
# from HR.permissions import check_master_access
# from .models import SMSConfiguration, GSMModemConfig, MobileModemConfig, APIConfig
# from django.contrib import messages


# # ─────────────────────────────────────────────
# # LIST VIEW
# # ─────────────────────────────────────────────
# def sms_config_list(request):
#     items = SMSConfiguration.objects.filter(status=True).order_by("id")
#     return render(request, "sms_config/list.html", {"items": items})


# # ─────────────────────────────────────────────
# # CREATE VIEW
# # ─────────────────────────────────────────────
# def sms_config_create(request):
#     if request.method == "POST":

#         mode = request.POST.get("mode")
#         status = request.POST.get("status") == "on"
#         # usage_list = request.POST.getlist("usage_types")

#         # 1️⃣ CHECK IF RECORD ALREADY EXISTS FOR THIS MODE
#         existing = SMSConfiguration.objects.filter(mode=mode, status=True).first()

#         if existing:
#             sms_config = existing
#             sms_config.status = status
#             sms_config.updated_by = request.user

#             # Merge usage types
#             # old = set(sms_config.usage_types or [])
#             # new = set(usage_list)
#             # sms_config.usage_types = list(old.union(new))
#             sms_config.save()
#         else:
#             # 2️⃣ CREATE NEW IF NOT EXISTS
#             sms_config = SMSConfiguration.objects.create(
#                 mode=mode,
#                 status=status,
#                 created_by=request.user,
#                 updated_by=request.user,
#                 # usage_types=usage_list,
#             )

#         # 3️⃣ IF DEFAULT CHECKBOX SELECTED
#         if request.POST.get("is_default") == "on":
#             SMSConfiguration.objects.update(is_default=False)
#             sms_config.is_default = True
#             sms_config.save(update_fields=["is_default"])

#         # ───────────────────────────────────────
#         #          APPEND MODE CONFIGS
#         # ───────────────────────────────────────

#         # 4️⃣ GSM MODE
#         if mode == "gsm":
#             ports = request.POST.getlist("gsm_port[]")
#             rates = request.POST.getlist("gsm_baudrate[]")
#             timeouts = request.POST.getlist("gsm_timeout[]")

#             for p, b, t in zip(ports, rates, timeouts):
#                 p = p.strip()
#                 if p:
#                     # prevent duplicate ports
#                     if not GSMModemConfig.objects.filter(sms_config=sms_config, gsm_port=p).exists():
#                         GSMModemConfig.objects.create(
#                             sms_config=sms_config,
#                             gsm_port=p,
#                             gsm_baudrate=b or None,
#                             gsm_timeout=t or None,
#                         )

#         # 5️⃣ MOBILE MODE
#         elif mode == "mobile":
#             ports = request.POST.getlist("mobile_port[]")
#             rates = request.POST.getlist("mobile_baudrate[]")
#             timeouts = request.POST.getlist("mobile_timeout[]")

#             for p, b, t in zip(ports, rates, timeouts):
#                 p = p.strip()
#                 if p:
#                     if not MobileModemConfig.objects.filter(sms_config=sms_config, mobile_port=p).exists():
#                         MobileModemConfig.objects.create(
#                             sms_config=sms_config,
#                             mobile_port=p,
#                             mobile_baudrate=b or None,
#                             mobile_timeout=t or None,
#                         )

#         # 6️⃣ API MODE
#         elif mode == "api":
#             urls = request.POST.getlist("api_url[]")
#             keys = request.POST.getlist("api_key[]")
#             senders = request.POST.getlist("api_sender[]")

#             for u, k, s in zip(urls, keys, senders):
#                 u = u.strip()
#                 if u:
#                     if not APIConfig.objects.filter(sms_config=sms_config, api_url=u).exists():
#                         APIConfig.objects.create(
#                             sms_config=sms_config,
#                             api_url=u,
#                             api_key=k or None,
#                             api_sender=s or None,
#                         )

#         messages.success(request, "SMS configuration updated (appended) successfully!")
#         return redirect("sms_config_list")

#     return render(request, "sms_config/create.html")

# # ─────────────────────────────────────────────
# # EDIT VIEW
# # ─────────────────────────────────────────────
# def sms_config_edit(request, pk):
#     sms_obj = get_object_or_404(SMSConfiguration, pk=pk)

#     if request.method == "POST":
#         mode = request.POST.get("mode")
#         status = request.POST.get("status") == "on"

#         # Update base settings
#         sms_obj.mode = mode
#         sms_obj.status = status
#         sms_obj.updated_by = request.user
#         # sms_obj.usage_types = request.POST.getlist("usage_types")  # FIXED HERE
#         sms_obj.save()

#         # HANDLE DEFAULT FLAG
#         if request.POST.get("is_default") == "on":
#             SMSConfiguration.objects.update(is_default=False)
#             sms_obj.is_default = True
#             sms_obj.save(update_fields=["is_default"])
#         else:
#             sms_obj.is_default = False
#             sms_obj.save(update_fields=["is_default"])

#         # REMOVE old configs for selected mode
#         GSMModemConfig.objects.filter(sms_config=sms_obj).delete()
#         MobileModemConfig.objects.filter(sms_config=sms_obj).delete()
#         APIConfig.objects.filter(sms_config=sms_obj).delete()

#         # ────────────── GSM MULTIPLE MODE ──────────────
#         if mode == "gsm":
#             ports = request.POST.getlist("gsm_port[]")
#             rates = request.POST.getlist("gsm_baudrate[]")
#             timeouts = request.POST.getlist("gsm_timeout[]")

#             for p, b, t in zip(ports, rates, timeouts):
#                 p = p.strip()
#                 if p:
#                     GSMModemConfig.objects.create(
#                         sms_config=sms_obj,
#                         gsm_port=p,
#                         gsm_baudrate=b or None,
#                         gsm_timeout=t or None,
#                     )

#         # ────────────── MOBILE MULTIPLE MODE ──────────────
#         elif mode == "mobile":
#             ports = request.POST.getlist("mobile_port[]")
#             rates = request.POST.getlist("mobile_baudrate[]")
#             timeouts = request.POST.getlist("mobile_timeout[]")

#             for p, b, t in zip(ports, rates, timeouts):
#                 p = p.strip()
#                 if p:
#                     MobileModemConfig.objects.create(
#                         sms_obj=sms_obj,
#                         mobile_port=p,
#                         mobile_baudrate=b or None,
#                         mobile_timeout=t or None,
#                     )

#         # ────────────── API MULTIPLE MODE ──────────────
#         elif mode == "api":
#             urls = request.POST.getlist("api_url[]")
#             keys = request.POST.getlist("api_key[]")
#             senders = request.POST.getlist("api_sender[]")

#             for u, k, s in zip(urls, keys, senders):
#                 u = u.strip()
#                 if u:
#                     APIConfig.objects.create(
#                         sms_config=sms_obj,
#                         api_url=u,
#                         api_key=k or None,
#                         api_sender=s or None,
#                     )

#         messages.success(request, "SMS configuration updated successfully!")
#         return redirect("sms_config_list")

#     # GET request – load all ports for template
#     context = {
#         "obj": sms_obj,
#         "all_gsm_modems": sms_obj.gsm_configs.all(),
#         "mobile_modems": sms_obj.mobile_configs.all(),
#         "api_configs": sms_obj.api_configs.all(),
#     }

#     return render(request, "sms_config/create.html", context)


# # ─────────────────────────────────────────────
# # DEACTIVATE VIEW
# # ─────────────────────────────────────────────

# def sms_config_deactivate(request, pk):
#     if not check_master_access(request.user, "Delete"):
#         return redirect("/")

#     try:
#         obj = SMSConfiguration.objects.get(pk=pk)
#         obj.status = False
#         obj.save(update_fields=["status"])
#         messages.success(request, "SMS configuration deleted successfully!")
#     except SMSConfiguration.DoesNotExist:
#         messages.error(request, "SMS configuration not found.")

#     return redirect("sms_config_list")



# # ─────────────────────────────────────────────
# # SET DEFAULT
# # ─────────────────────────────────────────────
# def sms_set_default(request, id):
#     obj = get_object_or_404(SMSConfiguration, id=id)

#     SMSConfiguration.objects.update(is_default=False)
#     obj.is_default = True
#     obj.save()

#     messages.success(request, "Default SMS configuration updated.")
#     return redirect("sms_config_list")












from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from sms_templates.constants import SMS_TEMPLATE_NAME_CHOICES
from .permissions import (
    can_view_sms_config, can_create_sms_config,
    can_edit_sms_config, can_delete_sms_config
)

from .models import (
    SMSConfiguration,
    GSMModemConfig,
    MobileModemConfig,
    APIConfig,
)


def _redirect_to_settings_sms_tab(request):
    settings_url = get_company_redirect_url(request, 'settings_page')
    return redirect(f"{settings_url}?tab=sms")

# ─────────────────────────────────────────────
# LIST VIEW
# ─────────────────────────────────────────────

@login_required
def sms_config_list(request):
    # Permission check - require view access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_sms_config(request.user)):
            messages.error(request, 'You do not have permission to view SMS Configuration.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view SMS Configuration.')
        return redirect_with_company('home')
    
    items = SMSConfiguration.objects.filter(status=True).order_by("id")

    context = {
        "items": items,
    }
    return render(request, "sms_config/list.html", context)


# ─────────────────────────────────────────────
# CREATE VIEW
# ─────────────────────────────────────────────

@login_required
def sms_config_create(request):
    # Permission check - require create access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_sms_config(request.user)):
            messages.error(request, 'You do not have permission to create SMS Configuration.')
            return _redirect_to_settings_sms_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to create SMS Configuration.')
        return _redirect_to_settings_sms_tab(request)
    
    if request.method == "POST":

        mode = request.POST.get("mode")
        status = request.POST.get("status") == "on"
        usage_types = request.POST.getlist("usage_types")  # ✅ USED FOR

        # 1️⃣ CHECK IF RECORD ALREADY EXISTS FOR THIS MODE
        existing = SMSConfiguration.objects.filter(mode=mode, status=True).first()

        if existing:
            sms_config = existing
            sms_config.status = status
            sms_config.updated_by = request.user

            # ✅ MERGE USAGE TYPES
            old_usage = set(sms_config.usage_types or [])
            new_usage = set(usage_types)
            sms_config.usage_types = list(old_usage.union(new_usage))

            sms_config.save()

        else:
            # 2️⃣ CREATE NEW CONFIG
            sms_config = SMSConfiguration.objects.create(
                mode=mode,
                status=status,
                usage_types=usage_types,
                created_by=request.user,
                updated_by=request.user,
            )

        # 3️⃣ DEFAULT CONFIG
        if request.POST.get("is_default") == "on":
            SMSConfiguration.objects.update(is_default=False)
            sms_config.is_default = True
            sms_config.save(update_fields=["is_default"])

        # ───────────────────────────────────────
        # MODE CONFIGS
        # ───────────────────────────────────────

        # GSM MODE
        if mode == "gsm":
            ports = request.POST.getlist("gsm_port[]")
            rates = request.POST.getlist("gsm_baudrate[]")
            timeouts = request.POST.getlist("gsm_timeout[]")

            for p, b, t in zip(ports, rates, timeouts):
                p = p.strip()
                if p and not GSMModemConfig.objects.filter(
                    sms_config=sms_config, gsm_port=p
                ).exists():
                    GSMModemConfig.objects.create(
                        sms_config=sms_config,
                        gsm_port=p,
                        gsm_baudrate=b or None,
                        gsm_timeout=t or None,
                    )

        # MOBILE MODE
        elif mode == "mobile":
            ports = request.POST.getlist("mobile_port[]")
            rates = request.POST.getlist("mobile_baudrate[]")
            timeouts = request.POST.getlist("mobile_timeout[]")

            for p, b, t in zip(ports, rates, timeouts):
                p = p.strip()
                if p and not MobileModemConfig.objects.filter(
                    sms_config=sms_config, mobile_port=p
                ).exists():
                    MobileModemConfig.objects.create(
                        sms_config=sms_config,
                        mobile_port=p,
                        mobile_baudrate=b or None,
                        mobile_timeout=t or None,
                    )

        # API MODE
        elif mode == "api":
            urls = request.POST.getlist("api_url[]")
            keys = request.POST.getlist("api_key[]")
            senders = request.POST.getlist("api_sender[]")

            for u, k, s in zip(urls, keys, senders):
                u = u.strip()
                if u and not APIConfig.objects.filter(
                    sms_config=sms_config, api_url=u
                ).exists():
                    APIConfig.objects.create(
                        sms_config=sms_config,
                        api_url=u,
                        api_key=k or None,
                        api_sender=s or None,
                    )

        messages.success(request, "SMS configuration created successfully!")
        return _redirect_to_settings_sms_tab(request)

    # GET REQUEST
    return render(
        request,
        "sms_config/create.html",
        {
            "usage_type_choices": SMS_TEMPLATE_NAME_CHOICES,  # ✅ FOR FORM
        },
    )


# ─────────────────────────────────────────────
# EDIT VIEW
# ─────────────────────────────────────────────

@login_required
def sms_config_edit(request, pk):
    # Permission check - require edit access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_edit_sms_config(request.user)):
            messages.error(request, 'You do not have permission to edit SMS Configuration.')
            return _redirect_to_settings_sms_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to edit SMS Configuration.')
        return _redirect_to_settings_sms_tab(request)
    
    sms_obj = get_object_or_404(SMSConfiguration, pk=pk)

    if request.method == "POST":
        mode = request.POST.get("mode")
        status = request.POST.get("status") == "on"
        usage_types = request.POST.getlist("usage_types")  # ✅ USED FOR

        # UPDATE BASE
        sms_obj.mode = mode
        sms_obj.status = status
        sms_obj.usage_types = usage_types
        sms_obj.updated_by = request.user
        sms_obj.save()

        # DEFAULT HANDLING
        if request.POST.get("is_default") == "on":
            SMSConfiguration.objects.update(is_default=False)
            sms_obj.is_default = True
        else:
            sms_obj.is_default = False
        sms_obj.save(update_fields=["is_default"])

        # CLEAR OLD MODE CONFIGS
        GSMModemConfig.objects.filter(sms_config=sms_obj).delete()
        MobileModemConfig.objects.filter(sms_config=sms_obj).delete()
        APIConfig.objects.filter(sms_config=sms_obj).delete()

        # GSM MODE
        if mode == "gsm":
            ports = request.POST.getlist("gsm_port[]")
            rates = request.POST.getlist("gsm_baudrate[]")
            timeouts = request.POST.getlist("gsm_timeout[]")

            for p, b, t in zip(ports, rates, timeouts):
                p = p.strip()
                if p:
                    GSMModemConfig.objects.create(
                        sms_config=sms_obj,
                        gsm_port=p,
                        gsm_baudrate=b or None,
                        gsm_timeout=t or None,
                    )

        # MOBILE MODE
        elif mode == "mobile":
            ports = request.POST.getlist("mobile_port[]")
            rates = request.POST.getlist("mobile_baudrate[]")
            timeouts = request.POST.getlist("mobile_timeout[]")

            for p, b, t in zip(ports, rates, timeouts):
                p = p.strip()
                if p:
                    MobileModemConfig.objects.create(
                        sms_config=sms_obj,
                        mobile_port=p,
                        mobile_baudrate=b or None,
                        mobile_timeout=t or None,
                    )

        # API MODE
        elif mode == "api":
            urls = request.POST.getlist("api_url[]")
            keys = request.POST.getlist("api_key[]")
            senders = request.POST.getlist("api_sender[]")

            for u, k, s in zip(urls, keys, senders):
                u = u.strip()
                if u:
                    APIConfig.objects.create(
                        sms_config=sms_obj,
                        api_url=u,
                        api_key=k or None,
                        api_sender=s or None,
                    )

        messages.success(request, "SMS configuration updated successfully!")
        return _redirect_to_settings_sms_tab(request)

    # GET REQUEST
    context = {
        "obj": sms_obj,
        "usage_type_choices": SMS_TEMPLATE_NAME_CHOICES,  # ✅ FOR FORM
        "all_gsm_modems": sms_obj.gsm_configs.all(),
        "mobile_modems": sms_obj.mobile_configs.all(),
        "api_configs": sms_obj.api_configs.all(),
    }
    return render(request, "sms_config/create.html", context)


# ─────────────────────────────────────────────
# DEACTIVATE VIEW
# ─────────────────────────────────────────────

@login_required
def sms_config_deactivate(request, pk):
    # Permission check - require delete access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_sms_config(request.user)):
            messages.error(request, 'You do not have permission to delete SMS Configuration.')
            return _redirect_to_settings_sms_tab(request)
    except Exception:
        messages.error(request, 'You do not have permission to delete SMS Configuration.')
        return _redirect_to_settings_sms_tab(request)

    obj = get_object_or_404(SMSConfiguration, pk=pk)
    obj.status = False
    obj.save(update_fields=["status"])

    messages.success(request, "SMS configuration deleted successfully!")
    return _redirect_to_settings_sms_tab(request)


# ─────────────────────────────────────────────
# SET DEFAULT
# ─────────────────────────────────────────────
def sms_set_default(request, id):
    obj = get_object_or_404(SMSConfiguration, id=id)

    SMSConfiguration.objects.update(is_default=False)
    obj.is_default = True
    obj.save(update_fields=["is_default"])

    messages.success(request, "Default SMS configuration updated.")
    return _redirect_to_settings_sms_tab(request)
