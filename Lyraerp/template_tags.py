"""
Template tags and filters for Lyra ERP
"""
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.filter
def add_company_code(view_name, company_code):
    """
    Custom filter to reverse a URL with company_code parameter.
    Usage in template: {% url view_name|add_company_code:request.company_code %}
    """
    if not company_code:
        return ""
    try:
        return reverse(view_name, kwargs={'company_code': company_code})
    except NoReverseMatch:
        return ""


@register.simple_tag(takes_context=True)
def company_url(context, view_name, *args, **kwargs):
    """
    Custom tag to reverse URLs with automatic company_code parameter.
    Usage in template: {% company_url 'view_name' arg1 arg2 %}
    """
    request = context.get('request')
    if request and hasattr(request, 'company_code') and request.company_code:
        kwargs['company_code'] = request.company_code
    try:
        return reverse(view_name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return ""
