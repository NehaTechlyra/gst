# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Unit
from .forms import UnitForm  
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
import csv

def unit_list(request):
    search_query = request.GET.get('q', '')
    units = Unit.objects.filter(status=True)

    if search_query:
        units = units.filter(
            Q(unit_name__icontains=search_query) 
          
        )
    units = units.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="units.csv"'
        writer = csv.writer(response)
        writer.writerow(["Unit Name"])
        for unit in units:
            writer.writerow([
                unit.unit_name or "",
            ])
        return response

    paginator = Paginator(units, 10)
    page_number = request.GET.get('page')
    unit_page = paginator.get_page(page_number)

    return render(request, "unit_list.html", {
        "units": unit_page,
        "search_query": search_query
    })


# @login_required
# def add_unit(request):
#     if request.method == "POST":
#         form = UnitForm(request.POST)
#         if form.is_valid():
#             unit = form.save(commit=False)
#             unit.created_by = request.user
#             unit.updated_by = request.user
#             unit.save()
#             messages.success(request, "Unit added successfully.")
#             return redirect('unit_list')
#     else:
#         form = UnitForm()

#     return render(request, 'add_unit.html', {'form': form, 'title': 'Add New Unit'})

@login_required
def add_unit(request):
    if request.method == "POST":
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.created_by = request.user
            # unit.updated_by = request.user
            unit.save()
            messages.success(request, "Unit added successfully.")
            return redirect_with_company('unit_list')  # Redirect to a list or detail page after saving
            
    else:
        form = UnitForm()

    # return render(request, "add_unit.html", {"form": form})
    return render(request, 'unit/add_unit.html', {'form': form, 'title': 'Add New Unit'})



@login_required
def edit_unit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)

    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            unit = form.save(commit=False)
            # Preserve created_by, set updated_by to current user
            if not unit.created_by:
                unit.created_by = request.user
            unit.updated_by = request.user
            unit.save()
            messages.success(request, "Unit edited successfully.")
            return redirect_with_company('unit_list')  # Change redirect as per your flow
    else:
        form = UnitForm(instance=unit)

    # return render(request, "add_unit.html", {"form": form})
    return render(request, 'unit/add_unit.html', {'form': form, 'title': 'Edit Unit'})

# Delete view
@require_POST
def delete_unit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    unit.status = False
    unit.save(update_fields=["status"])
    messages.success(request, "Unit deleted successfully.")
    return redirect_with_company('unit_list')
        