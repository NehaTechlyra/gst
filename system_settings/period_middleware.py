"""
Period Locking Decorators & Middleware
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Decorators and utilities for enforcing period locking on views.

Usage:
    from system_settings.period_middleware import check_period_locked_for_date
    
    @login_required
    @check_period_locked_for_date(date_param='date')  # GET parameter name
    def edit_item(request):
        ...
"""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from Lyraerp.utils.redirect_utils import redirect_with_company
from datetime import datetime
from .period_validators import check_period_locked, PeriodLockedError, is_period_locked


def check_period_locked_for_date(date_param='date', date_field='date'):
    """
    Decorator to check if a date parameter falls within a locked period.
    
    Args:
        date_param: GET/POST parameter name containing the date
        date_field: Name of the field in the form (for error messages)
    
    Usage:
        @check_period_locked_for_date(date_param='transaction_date')
        def edit_transaction(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                # Get date from GET or POST parameters
                date_str = request.GET.get(date_param) or request.POST.get(date_param)
                
                if date_str:
                    # Parse the date string
                    try:
                        if isinstance(date_str, str):
                            # Try parsing ISO format first (YYYY-MM-DD)
                            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:
                            check_date = date_str
                    except (ValueError, TypeError):
                        # Invalid date format, allow view to handle it
                        pass
                    else:
                        # Check if period is locked
                        check_period_locked(check_date, request.user)
                
                # No exception raised, proceed with view
                return view_func(request, *args, **kwargs)
            
            except PeriodLockedError as e:
                # Period is locked, redirect with error message
                messages.error(request, str(e))
                # Redirect back to previous page or default URL
                return redirect_with_company(request.META.get('HTTP_REFERER', '/'))
        
        return wrapper
    return decorator


def check_period_locked_post_only(date_param='date'):
    """
    Decorator to check period lock ONLY on POST requests (not GET).
    Useful for forms where GET is just for display, POST is for saving.
    
    Usage:
        @check_period_locked_post_only(date_param='date')
        def edit_item(request):
            if request.method == 'POST':
                # POST validation happens automatically
                ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Only check on POST requests
            if request.method == 'POST':
                try:
                    date_str = request.POST.get(date_param)
                    
                    if date_str:
                        try:
                            if isinstance(date_str, str):
                                check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            else:
                                check_date = date_str
                        except (ValueError, TypeError):
                            pass  # Invalid date, let view handle it
                        else:
                            # Check if period is locked
                            check_period_locked(check_date, request.user)
                
                except PeriodLockedError as e:
                    messages.error(request, str(e))
                    return redirect_with_company(request.META.get('HTTP_REFERER', '/'))
            
            # Allow view to process
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def inject_period_lock_status(view_func):
    """
    Decorator to inject period lock status into context.
    Useful for displaying lock status on forms.
    
    Usage:
        @inject_period_lock_status
        def edit_item(request):
            context = {...}
            return render(request, 'template.html', context)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Try to inject period lock info into context if response has context_data
        try:
            if hasattr(response, 'context_data'):
                from .period_validators import get_fiscal_year_for_date
                from django.utils import timezone
                
                today = timezone.now().date()
                current_fy = get_fiscal_year_for_date(today)
                
                response.context_data['current_fiscal_year'] = current_fy
                response.context_data['is_period_locked'] = (
                    current_fy.is_locked if current_fy else False
                )
        except:
            pass  # If context injection fails, just continue
        
        return response
    
    return wrapper


class PeriodLockValidationMixin:
    """
    Mixin for class-based views to enforce period locking.
    
    Usage:
        from django.views import UpdateView
        
        class ItemEditView(PeriodLockValidationMixin, UpdateView):
            model = Item
            form_class = ItemForm
            date_field = 'created_date'  # Field to check for lock
            
            def get_lock_date(self, form):
                # Return the date to check, defaults to today
                return form.cleaned_data.get('date') or timezone.now().date()
    """
    
    date_field = 'date'  # Override in subclass
    
    def form_valid(self, form):
        """Check period lock before saving form"""
        try:
            # Get the date to check for locking
            if hasattr(self, 'get_lock_date'):
                check_date = self.get_lock_date(form)
            else:
                check_date = form.cleaned_data.get(self.date_field) or \
                           getattr(self.object, self.date_field, None)
            
            # Validate period is not locked
            if check_date:
                from .period_validators import check_period_locked
                check_period_locked(check_date, self.request.user)
        
        except PeriodLockedError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        
        # Period is open, proceed with normal save
        return super().form_valid(form)


def get_period_lock_warning(date_obj):
    """
    Generate a warning message if a date is in a locked period.
    Returns None if period is open, otherwise returns warning message.
    
    Usage in template:
        {% if period_warning %}
        <div class="alert alert-warning">{{ period_warning }}</div>
        {% endif %}
    """
    from .period_validators import get_fiscal_year_for_date
    
    fiscal_year = get_fiscal_year_for_date(date_obj)
    if not fiscal_year:
        return None
    
    if fiscal_year.is_locked:
        return (
            f'⚠️ <strong>WARNING:</strong> The period '
            f'<strong>{fiscal_year.name}</strong> ({fiscal_year.start_date.strftime("%d %b %Y")} - '
            f'{fiscal_year.end_date.strftime("%d %b %Y")}) is LOCKED. '
            f'You will not be able to edit this transaction.'
        )
    
    return None
