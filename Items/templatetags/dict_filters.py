# Items/templatetags/dict_filters.py
# Also create Items/templatetags/__init__.py (empty file)

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")

@register.filter  
def dict_values(d):
    if isinstance(d, dict):
        return list(d.values())
    return []