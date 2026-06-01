from django.shortcuts import redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow login, logout, and static/media URLs without login
        allowed_urls = [
            reverse('login'),
            reverse('logout'),
        ]
        if not request.user.is_authenticated:
            if request.path not in allowed_urls and not request.path.startswith('/static/'):
                return redirect_with_company('login')
        return self.get_response(request)


class SiteBlockMiddleware:
    """Block access site-wide when settings.SITE_BLOCK is True.

    Behavior:
    - If SITE_BLOCK is False: do nothing.
    - Allow static/media/admin/login/logout and health-check paths.
    - Allow staff/superuser users to bypass the block.
    - All other requests return a simple blocked page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only active when explicitly turned on
        if not getattr(settings, 'SITE_BLOCK', False):
            return self.get_response(request)

        # Always allow static/media and admin paths
        path = request.path
        if path.startswith(settings.STATIC_URL) or path.startswith('/media/') or path.startswith('/admin/'):
            return self.get_response(request)

        # Allow login/logout and other safe urls
        try:
            allowed = {reverse('login'), reverse('logout')}
        except Exception:
            allowed = set()
        if path in allowed:
            return self.get_response(request)

        # Superusers and staff bypass the block
        if getattr(request, 'user', None) and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return self.get_response(request)

        # Render a simple blocked page
        return render(request, 'site_blocked.html', status=403)
