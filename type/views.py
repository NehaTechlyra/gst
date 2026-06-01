from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Type
from .forms import TypeForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
import csv

def type_list(request):
    search_query = request.GET.get('q', '')
    types = Type.objects.filter(status=True)

    if search_query:
        types = types.filter(Q(type_name__icontains=search_query))

    types = types.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="types.csv"'
        writer = csv.writer(response)
        writer.writerow(["Type Name"])
        for t in types:
            writer.writerow([
                t.type_name or "",
            ])
        return response

    paginator = Paginator(types, 10)
    page_number = request.GET.get('page')
    type_page = paginator.get_page(page_number)

    return render(request, "type_list.html", {"types": type_page, "search_query": search_query})



@login_required
def add_type(request):
    if request.method == "POST":
        form = TypeForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Type added successfully.")
            return redirect_with_company('type_list')
    else:
        form = TypeForm()

    return render(request, 'add_type.html', {'form': form, 'title': 'Add New Type'})


@login_required
def edit_type(request, pk):
    obj = get_object_or_404(Type, pk=pk)

    if request.method == "POST":
        form = TypeForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.created_by:
                obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(request, "Type edited successfully.")
            return redirect_with_company('type_list')
    else:
        form = TypeForm(instance=obj)

    return render(request, 'add_type.html', {'form': form, 'title': 'Edit Type'})


@require_POST
def delete_type(request, pk):
    obj = get_object_or_404(Type, pk=pk)
    obj.status = False
    obj.save(update_fields=["status"])
    messages.success(request, "Type deleted successfully.")
    return redirect_with_company('type_list')
