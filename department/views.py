from django.shortcuts import render, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.urls import NoReverseMatch, reverse
from .models import Department


def department_list(request):
    items = Department.objects.filter(status=True).order_by('department_name')
    return render(request, 'department/list.html', {'items': items})


def department_create(request):
    next_target = request.GET.get('next') or request.POST.get('next')
    # require master Create permission
    from user.utils import has_permission
    from HR.permissions import check_master_access
    if not check_master_access(request.user, 'Create'):
        return redirect_with_company(request, '/')
    if request.method == 'POST':
        name = request.POST.get('department_name')
        status = True if request.POST.get('status') == 'on' else False
        if name:
            Department.objects.create(department_name=name, status=status)
            if next_target:
                # If next_target looks like an anchor name (no leading '#'),
                # prefer redirecting to admin dashboard with the anchor.
                if not next_target.startswith('#'):
                    # Try to reverse it as a named URL first; if that fails,
                    # treat it as an anchor on the admin dashboard.
                    try:
                        reverse(next_target)
                        # Successfully reversed, so go there directly with company_code
                        return redirect_with_company(request, next_target)
                    except NoReverseMatch:
                        # Not a valid view name, treat as anchor
                        next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')
    return render(request, 'department/create.html', {'next': next_target})


def department_deactivate(request, pk):
    try:
        obj = Department.objects.get(pk=pk)
        obj.status = False
        obj.save()
    except Department.DoesNotExist:
        pass
    # require master Delete permission
    from HR.permissions import check_master_access
    if not check_master_access(request.user, 'Delete'):
        return redirect_with_company(request, '/')
    next_target = request.GET.get('next') or request.POST.get('next')
    if next_target:
        if not next_target.startswith('#'):
            # try to reverse as named url, else treat as anchor
            try:
                reverse(next_target)
                # Successfully reversed, so go there directly with company_code
                return redirect_with_company(request, next_target)
            except NoReverseMatch:
                # Not a valid view name, treat as anchor
                next_target = '#' + next_target
        url = get_company_redirect_url(request, 'admin_dashboard') + next_target
        return redirect(url)
    return redirect_with_company(request, 'admin_dashboard')


def department_edit(request, pk):
    try:
        obj = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return redirect_with_company(request, 'admin_dashboard')

    next_target = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        name = request.POST.get('department_name')
        status = True if request.POST.get('status') == 'on' else False
        if name:
            obj.department_name = name
            obj.status = status
            obj.save()
            if next_target:
                # If next_target starts with '#', it's an anchor on admin_dashboard
                if next_target.startswith('#'):
                    url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                    return redirect(url)
                # Try reversing the next_target as a named URL (safe); if it fails,
                # treat it as an anchor name on the admin dashboard.
                try:
                    reverse(next_target)
                    # Successfully reversed, so go there directly with company_code
                    return redirect_with_company(request, next_target)
                except NoReverseMatch:
                    # Not a valid view name, treat as anchor
                    url = get_company_redirect_url(request, 'admin_dashboard') + '#' + next_target
                    return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')

    return render(request, 'department/create.html', {'obj': obj, 'next': next_target})
