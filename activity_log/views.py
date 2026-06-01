from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ActivityLog

@login_required
def activity_log_list(request):
    """View to display activity logs with filtering."""
    logs = ActivityLog.objects.select_related('user', 'content_type').all()
    
    # Filtering
    action_filter = request.GET.get('action')
    model_filter = request.GET.get('model')
    user_filter = request.GET.get('user')
    search = request.GET.get('q')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if search:
        logs = logs.filter(
            Q(object_repr__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filters
    actions = ActivityLog.objects.values_list('action', flat=True).distinct()
    models = ActivityLog.objects.values_list('model_name', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'actions': actions,
        'models': models,
        'current_action': action_filter,
        'current_model': model_filter,
        'current_user': user_filter,
        'search': search,
    }
    
    return render(request, 'activity_log/log_list.html', context)

@login_required
def activity_log_detail(request, pk):
    """View to display detailed activity log."""
    log = ActivityLog.objects.get(pk=pk)
    return render(request, 'activity_log/log_detail.html', {'log': log})


@login_required
def model_activity_log_list(request,model):
    """View to display activity logs with filtering."""
    logs = ActivityLog.objects.select_related('user', 'content_type').all()
    
    # Filtering
    action_filter = request.GET.get('action')
    # model_filter = request.GET.get('model')
    model_filter = model

    user_filter = request.GET.get('user')
    search = request.GET.get('q')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if search:
        logs = logs.filter(
            Q(object_repr__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filters
    actions = ActivityLog.objects.values_list('action', flat=True).distinct()
    models = ActivityLog.objects.values_list('model_name', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'actions': actions,
        'models': models,
        'current_action': action_filter,
        'current_model': model_filter,
        'current_user': user_filter,
        'search': search,
    }
    
    return render(request, 'activity_log/model_log.html', context)




@login_required
def model_object_activity_log_list(request, model, object_id):
    logs = ActivityLog.objects.select_related(
        'user', 'content_type'
    ).filter(
        model_name=model,
        object_id=object_id
    )
    print("model",model)
    print("object_id",object_id)
    print("logs",logs)

    # Filters
    action_filter = request.GET.get('action')
    search = request.GET.get('q')

    if action_filter:
        logs = logs.filter(action=action_filter)

    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(object_repr__icontains=search)
        )

    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    actions = ActivityLog.objects.values_list('action', flat=True).distinct()

    context = {
        'page_obj': page_obj,
        'actions': actions,
        'current_action': action_filter,
        'model_name': model,
        'object_id': object_id,
    }

    return render(
        request,
        'activity_log/object_log.html',
        context
    )