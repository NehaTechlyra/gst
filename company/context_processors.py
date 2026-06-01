# from company_settings.models import LicenseKey
# from .constants import SYSTEM_MODULES

# def license_context(request):
#     """
#     Context processor to add license and module information to all templates.
#     This makes module visibility available throughout the application.
#     """
#     context = {
#         'licensed_modules': [],
#         'license_info': None,
#         'module_access': {}
#     }
    
#     # Skip for unauthenticated users
#     if not request.user.is_authenticated:
#         return context
    
#     # Superusers see everything
#     if request.user.is_superuser:
#         context['licensed_modules'] = [m['name'] for m in SYSTEM_MODULES]
#         context['module_access'] = {m['code']: True for m in SYSTEM_MODULES}
#         return context
    
#     # Get user's company
#     company = getattr(request.user, 'company', None)
    
#     if not company:
#         return context
    
#     # Get license
#     try:
#         license_obj = LicenseKey.objects.get(company=company)
        
#         # Check if license is valid
#         if license_obj.is_active and not license_obj.is_expired():
#             # Build visible modules list
#             licensed_modules = []
#             module_access = {}
            
#             for module in SYSTEM_MODULES:
#                 has_access = license_obj.has_module_access(module['code'])
#                 module_access[module['code']] = has_access
                
#                 if has_access:
#                     licensed_modules.append(module['name'])
            
#             context['licensed_modules'] = licensed_modules
#             context['module_access'] = module_access
#             context['license_info'] = {
#                 'is_active': license_obj.is_active,
#                 'is_expired': license_obj.is_expired(),
#                 'expiry_date': license_obj.expiry_date,
#                 'max_users': license_obj.max_users
#             }
#     except LicenseKey.DoesNotExist:
#         pass
    
#     return context



from .constants import SYSTEM_MODULES

def license_context(request):
    """
    Context processor to add license and module information to all templates.
    This makes module visibility available throughout the application.

    Priority order:
    1. Superuser → full access
    2. request.license_info (set by LicenseInfoMiddleware) → use allowed_modules
       - allowed_modules = None  → full access (trial / enterprise license)
       - allowed_modules = list  → only those modules
       - allowed_modules = []    → no modules (expired / blocked)
    3. Fallback: empty (no access)
    """
    all_module_names = [m['name'] for m in SYSTEM_MODULES]
    all_module_codes = {m['code']: True for m in SYSTEM_MODULES}

    context = {
        'licensed_modules': [],
        'license_info': None,
        'module_access': {},
        # Convenience flag used in base.html sidebar guards:
        #   {% if all_modules_visible or 'Purchase' in licensed_modules %}
        'all_modules_visible': False,
    }

    # ── Unauthenticated ──────────────────────────────────────────────────────
    if not request.user.is_authenticated:
        return context

    # ── Superuser: full access ────────────────────────────────────────────────
    if request.user.is_superuser:
        context['licensed_modules']  = all_module_names
        context['module_access']     = all_module_codes
        context['all_modules_visible'] = True
        return context

    # ── Use license_info injected by LicenseInfoMiddleware ───────────────────
    license_info = getattr(request, 'license_info', None)

    if license_info:
        allowed_modules = license_info.get('allowed_modules')  # None OR list

        # None means unrestricted (trial or full/enterprise license)
        if allowed_modules is None:
            context['licensed_modules']    = all_module_names
            context['module_access']       = all_module_codes
            context['all_modules_visible'] = True

        # Non-empty list: only the specified modules are licensed
        elif allowed_modules:
            # allowed_modules contains module *codes* (e.g. 'SALES', 'HR')
            # Map codes → names for template `in` checks
            code_set = set(allowed_modules)
            licensed_modules = []
            module_access    = {}

            for m in SYSTEM_MODULES:
                has_access = m['code'] in code_set
                module_access[m['code']] = has_access
                if has_access:
                    licensed_modules.append(m['name'])

            context['licensed_modules'] = licensed_modules
            context['module_access']    = module_access

        # Empty list: no modules (expired / blocked) — leave defaults (empty)

        # Always forward the raw license_info dict for template use
        context['license_info'] = license_info
        return context

    # ── Fallback: no license_info on request (middleware not run?) ───────────
    # Attempt a direct DB lookup so the app still works in isolation.
    try:
        from company_settings.models import LicenseKey

        company = getattr(request.user, 'company', None)
        if not company:
            return context

        license_obj = LicenseKey.objects.get(company=company)

        if license_obj.is_active and not license_obj.is_expired():
            licensed_modules = []
            module_access    = {}

            for m in SYSTEM_MODULES:
                has_access = license_obj.has_module_access(m['code'])
                module_access[m['code']] = has_access
                if has_access:
                    licensed_modules.append(m['name'])

            context['licensed_modules'] = licensed_modules
            context['module_access']    = module_access
            context['license_info'] = {
                'is_active':   license_obj.is_active,
                'is_expired':  license_obj.is_expired(),
                'expiry_date': license_obj.expiry_date,
                'max_users':   license_obj.max_users,
            }

    except Exception:
        pass

    return context