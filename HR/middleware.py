from django.template import TemplateDoesNotExist
from django.http import HttpResponse


class TemplateFallbackMiddleware:
    """Catch TemplateDoesNotExist and return a readable fallback instead of a blank page."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except TemplateDoesNotExist as exc:
            message = f"Template not found: {exc}.\nPlease check template paths."
            return HttpResponse(f"<pre>{message}</pre>", status=500)
