from django.shortcuts import render, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from .models import Allowances


def allowances_list(request):
    items = Allowances.objects.filter(status=True).order_by('allowances_name')
    return render(request, 'allowances/list.html', {'items': items})


def allowances_create(request):
    # allow caller to specify return target (e.g., ?next=#allowances)
    next_target = request.GET.get('next') or request.POST.get('next')
    # require master Create permission
    from HR.permissions import check_master_access
    if not check_master_access(request.user, 'Create'):
        return redirect_with_company(request, '/')
    if request.method == 'POST':
        name = request.POST.get('allowances_name') or request.POST.get('allowance_name')
        status = True if request.POST.get('status') == 'on' else False
        if name:
            Allowances.objects.create(allowances_name=name, status=status)
            if next_target:
                # redirect back to admin with fragment #section
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')
    return render(request, 'allowances/create.html', {'next': next_target})


def allowances_deactivate(request, pk):
    try:
        obj = Allowances.objects.get(pk=pk)
        obj.status = False
        obj.save()
    except Allowances.DoesNotExist:
        pass
    # preserve return target if provided
    next_target = request.GET.get('next') or request.POST.get('next')
    if next_target:
        if not next_target.startswith('#'):
            next_target = '#' + next_target
        url = get_company_redirect_url(request, 'admin_dashboard') + next_target
        return redirect(url)
    return redirect_with_company(request, 'admin_dashboard')
    

def allowances_edit(request, pk):
    try:
        obj = Allowances.objects.get(pk=pk)
    except Allowances.DoesNotExist:
        return redirect_with_company(request, 'admin_dashboard')

    if request.method == 'POST':
        name = request.POST.get('allowances_name') or request.POST.get('allowance_name')
        status = True if request.POST.get('status') == 'on' else False
        if name:
            obj.allowances_name = name
            obj.status = status
            obj.save()
            next_target = request.GET.get('next') or request.POST.get('next')
            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')

    next_target = request.GET.get('next')
    return render(request, 'allowances/create.html', {'obj': obj, 'next': next_target})
 
