from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_redirect_url
from django.urls import NoReverseMatch
from django.utils.timezone import now
from .models import PersonalDocumentType


def personal_document_type_list(request):
    """List all active document types"""
    items = PersonalDocumentType.objects.filter(status=True).order_by('name')
    return render(request, 'personal_document_type/list.html', {'items': items})


def personal_document_type_create(request):
    """Create a new document type"""
    next_target = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        name = request.POST.get('name')
        example_format = request.POST.get('example_format', '')
        status = True if request.POST.get('status') == 'on' else False

        if name:
            # Use get_or_create to handle duplicates gracefully
            # If the document type already exists (inactive), it will be reactivated
            obj, created = PersonalDocumentType.objects.get_or_create(
                name=name,
                defaults={
                    'example_format': example_format,
                    'status': status,
                    'created_by': None,
                    'updated_by': None
                }
            )
            
            # If it already existed, update it (in case status or example_format changed)
            if not created:
                obj.example_format = example_format
                obj.status = status
                obj.updated_at = now()
                obj.updated_by = None
                obj.save()
            
            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')

    return render(request, 'personal_document_type/create.html', {'next': next_target})


def personal_document_type_edit(request, pk):
    """Edit an existing document type"""
    next_target = request.GET.get('next') or request.POST.get('next')
    obj = get_object_or_404(PersonalDocumentType, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        example_format = request.POST.get('example_format', '')
        status = True if request.POST.get('status') == 'on' else False

        if name:
            obj.name = name
            obj.example_format = example_format
            obj.status = status
            obj.updated_at = now()
            obj.updated_by = None
            obj.save()

            if next_target:
                if not next_target.startswith('#'):
                    next_target = '#' + next_target
                url = get_company_redirect_url(request, 'admin_dashboard') + next_target
                return redirect(url)
            return redirect_with_company(request, 'admin_dashboard')

    return render(request, 'personal_document_type/create.html', {'obj': obj, 'next': next_target})


def personal_document_type_deactivate(request, pk):
    """Deactivate a document type"""
    try:
        obj = PersonalDocumentType.objects.get(pk=pk)
        obj.status = False
        obj.save()
    except PersonalDocumentType.DoesNotExist:
        pass

    next_target = request.GET.get('next') or request.POST.get('next')
    if next_target:
        if not next_target.startswith('#'):
            next_target = '#' + next_target
        url = get_company_redirect_url(request, 'admin_dashboard') + next_target
        return redirect(url)
    return redirect_with_company(request, 'admin_dashboard')
