from django.shortcuts import render, redirect
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.urls import NoReverseMatch
from .models import Designations
from user.utils import has_permission
from HR.permissions import check_master_access


def designation_list(request):
    items = Designations.objects.filter(status=True).order_by('designation_name')
    return render(request, 'designation/list.html', {'items': items})


def designation_create(request):
    # plain HTML form handling (no ModelForm)
    next_target = request.GET.get('next') or request.POST.get('next')
    # require master Create permission
    if not check_master_access(request.user, 'Create'):
        return redirect_with_company(request, '/')
    if request.method == 'POST':
        dept_id = request.POST.get('departments')
        name = request.POST.get('designation_name')
        status = True if request.POST.get('status') == 'on' else False
        if name and dept_id:
            Designations.objects.create(departments_id=dept_id, designation_name=name, status=status)
            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')
    # when GET or invalid POST just render the form
    # load departments for the select in template via context
    from department.models import Department
    departments = Department.objects.filter(status=True)
    return render(request, 'designation/create.html', {'departments': departments})


def designation_deactivate(request, pk):
    # Soft-delete by setting status to False
    try:
        obj = Designations.objects.get(pk=pk)
        obj.status = False
        obj.save()
    except Designations.DoesNotExist:
        pass
    # require master Delete permission
    if not check_master_access(request.user, 'Delete'):
        return redirect_with_company(request, '/')
    return redirect_with_company(request, 'admin_dashboard')


def designation_edit(request, pk):
    from department.models import Department
    next_target = request.GET.get('next') or request.POST.get('next')
    try:
        obj = Designations.objects.get(pk=pk)
    except Designations.DoesNotExist:
        return redirect_with_company(request, 'admin_dashboard')

    # require master Edit permission to submit changes
    if request.method == 'POST' and not check_master_access(request.user, 'Edit'):
        return redirect_with_company(request, '/')
    if request.method == 'POST':
        dept_id = request.POST.get('departments')
        name = request.POST.get('designation_name')
        status = True if request.POST.get('status') == 'on' else False
        if name and dept_id:
            obj.departments_id = dept_id
            obj.designation_name = name
            obj.status = status
            obj.save()
            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')

    departments = Department.objects.filter(status=True)
    return render(request, 'designation/create.html', {'departments': departments, 'obj': obj, 'next': next_target})


