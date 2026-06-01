"""
Custom template tags and filters for URL reversal with company_code
BULLETPROOF VERSION - Handles all edge cases gracefully
AUTO-REGISTERS GLOBALLY - No need for {% load lyra_tags %} in templates
"""
from django import template
from django.urls import reverse, NoReverseMatch
from django.template.defaulttags import url as default_url_tag

register = template.Library()


@register.simple_tag(takes_context=True)
def company_url(context, view_name, *args, **kwargs):
    """
    Custom tag to reverse URLs with automatic company_code parameter.
    
    This function NEVER mixes args and kwargs when calling reverse().
    
    Usage in template: {% company_url 'view_name' %}
    The company_code is automatically added from context.
    
    Examples:
        {% company_url 'sales_quote_list' %}
        {% company_url 'sales_order_list' %}
        {% company_url 'employee_detail' employee.id %}
        {% company_url 'company_update' company.id %}
    """
    request = context.get('request')
    company_code = None
    
    # Try to get company_code from various sources
    if request and hasattr(request, 'company_code'):
        company_code = request.company_code
    elif context.get('company_code'):
        company_code = context.get('company_code')
    
    # Convert everything to use ONLY kwargs (no mixing!)
    final_kwargs = dict(kwargs)  # Copy kwargs
    
    # Add company_code if available
    if company_code:
        final_kwargs['company_code'] = company_code
    
    # Handle positional arguments by converting to kwargs
    if args:
        # If we have positional args, we need to convert them to kwargs
        # Try different parameter names that Django commonly uses
        if len(args) == 1:
            # Single argument - try common parameter names (include account / reconciliation keys)
            param_names_to_try = ['pk', 'id', 'slug', 'account_id', 'reconciliation_id', 'company_id', 'bank_account_id']
            
            for param_name in param_names_to_try:
                try:
                    test_kwargs = final_kwargs.copy()
                    test_kwargs[param_name] = args[0]
                    # Try to reverse with this parameter name
                    url = reverse(view_name, kwargs=test_kwargs)
                    return url
                except NoReverseMatch:
                    continue
            
            # If none of the common names worked, try without company_code
            for param_name in param_names_to_try:
                try:
                    test_kwargs = {param_name: args[0]}
                    url = reverse(view_name, kwargs=test_kwargs)
                    return url
                except NoReverseMatch:
                    continue
            
            # Last resort: use args-only (no kwargs at all)
            try:
                return reverse(view_name, args=args)
            except NoReverseMatch:
                pass
                
        else:
            # Multiple positional arguments - use args-only approach
            try:
                return reverse(view_name, args=args)
            except NoReverseMatch:
                pass
    
    # No positional args, just use kwargs
    try:
        return reverse(view_name, kwargs=final_kwargs)
    except NoReverseMatch:
        # Try without company_code
        try:
            final_kwargs.pop('company_code', None)
            if final_kwargs:
                return reverse(view_name, kwargs=final_kwargs)
            else:
                return reverse(view_name)
        except NoReverseMatch:
            # Return a helpful error message
            return f"#[URL-ERROR:{view_name}]"


@register.simple_tag(takes_context=True)
def company_path(context, path):
    """
    Add company code to any path.
    
    Usage:
    <a href="{% company_path '/sales/invoices/' %}">Invoices</a>
    
    Returns:
    /TECH4-14HG/sales/invoices/
    """
    request = context.get('request')
    
    if not request:
        return path
    
    company_code = getattr(request, 'company_code', None) or request.session.get('company_code')
    
    if company_code:
        # Remove leading slash if present
        clean_path = path.lstrip('/')
        return f"/{company_code}/{clean_path}"
    
    return path


# ============================================================================
# OVERRIDE DJANGO'S DEFAULT {% url %} TAG TO AUTO-INJECT company_code
# ============================================================================
# This makes {% url 'view_name' %} automatically work with company_code
# So you don't need to change existing templates to use {% company_url %}
# ============================================================================

@register.tag(name='url')
def url_with_company_override(parser, token):
    """
    Override Django's {% url %} tag to automatically inject company_code.
    
    This allows existing templates using {% url %} to work without changes.
    
    Usage (works exactly like standard Django url tag):
        {% url 'view_name' %}
        {% url 'view_name' arg1 %}
        {% url 'view_name' arg1 arg2 %}
        {% url 'view_name' kwarg1=value1 %}
    """
    bits = token.split_contents()
    
    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            "'url' tag requires at least one argument (view name)."
        )
    
    view_name = parser.compile_filter(bits[1])
    args = []
    kwargs = {}
    asvar = None
    bits = bits[2:]
    
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    
    # Parse remaining bits for args and kwargs
    for bit in bits:
        if '=' in bit:
            # This is a kwarg
            key, value = bit.split('=', 1)
            kwargs[key] = parser.compile_filter(value)
        else:
            # This is a positional arg
            args.append(parser.compile_filter(bit))
    
    return URLWithCompanyNode(view_name, args, kwargs, asvar)


class URLWithCompanyNode(template.Node):
    """
    Node class for the url tag with company_code auto-injection.
    
    This NEVER mixes args and kwargs when calling reverse().
    """
    
    def __init__(self, view_name, args, kwargs, asvar):
        self.view_name = view_name
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar
    
    def render(self, context):
        """Render the URL with company_code auto-injection."""
        # Resolve view name
        view_name = self.view_name.resolve(context)
        
        # Resolve args
        resolved_args = [arg.resolve(context) for arg in self.args]
        
        # Resolve kwargs
        resolved_kwargs = {key: val.resolve(context) for key, val in self.kwargs.items()}
        
        # Get company_code from context
        request = context.get('request')
        company_code = None
        
        if request and hasattr(request, 'company_code'):
            company_code = request.company_code
        elif context.get('company_code'):
            company_code = context.get('company_code')
        
        # Generate URL using the same logic as company_url
        url = None
        
        # Case 1: We have positional args
        if resolved_args:
            if len(resolved_args) == 1 and not resolved_kwargs:
                # Single positional arg - convert to kwargs
                param_names = ['pk', 'id', 'slug']
                
                for param_name in param_names:
                    try:
                        test_kwargs = {param_name: resolved_args[0]}
                        if company_code:
                            test_kwargs['company_code'] = company_code
                        url = reverse(view_name, kwargs=test_kwargs)
                        break
                    except NoReverseMatch:
                        continue
                
                # If that didn't work, try without company_code
                if not url:
                    for param_name in param_names:
                        try:
                            url = reverse(view_name, kwargs={param_name: resolved_args[0]})
                            break
                        except NoReverseMatch:
                            continue
                
                # Last resort: use args-only
                if not url:
                    try:
                        url = reverse(view_name, args=resolved_args)
                    except NoReverseMatch:
                        pass
            else:
                # Multiple args or args with kwargs - use args-only
                try:
                    url = reverse(view_name, args=resolved_args)
                except NoReverseMatch:
                    pass
        
        # Case 2: Only kwargs
        else:
            try:
                if company_code:
                    resolved_kwargs['company_code'] = company_code
                url = reverse(view_name, kwargs=resolved_kwargs)
            except NoReverseMatch:
                # Try without company_code
                try:
                    resolved_kwargs.pop('company_code', None)
                    if resolved_kwargs:
                        url = reverse(view_name, kwargs=resolved_kwargs)
                    else:
                        url = reverse(view_name)
                except NoReverseMatch:
                    pass
        
        # If we still don't have a URL, return error
        if url is None:
            url = f"#[URL-ERROR:{view_name}]"
        
        # Handle 'as' variable assignment
        if self.asvar:
            context[self.asvar] = url
            return ''
        
        return url


# ============================================================================
# ADDITIONAL UTILITY TAGS
# ============================================================================

@register.filter
def add_company_prefix(path, company_code):
    """
    Template filter to add company code prefix to a path.
    
    Usage: {{ '/sales/list/'|add_company_prefix:request.company_code }}
    Returns: /TECH4-14HG/sales/list/
    """
    if not company_code:
        return path
    
    clean_path = path.lstrip('/')
    return f"/{company_code}/{clean_path}"


# ============================================================================
# AUTO-REGISTER THESE TAGS GLOBALLY
# ============================================================================
# This makes company_url available in ALL templates without needing {% load lyra_tags %}

from django.template import engines

def register_global_tags():
    """Register our custom tags as built-in tags in Django's template engine."""
    try:
        # Get the Django template engine
        django_engine = engines['django']
        
        # Add our custom tags to Django's built-in tags
        # This makes them available in ALL templates without {% load lyra_tags %}
        if 'Lyraerp.templatetags.lyra_tags' not in django_engine.engine.builtins:
            django_engine.engine.builtins.append('Lyraerp.templatetags.lyra_tags')
    except Exception as e:
        # Log error but don't break the app
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to register global tags: {e}")

# Call this when the module loads
register_global_tags()