# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Brand
from .forms import BrandForm  
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
import csv

def brand_list(request):
    search_query = request.GET.get('q', '')
    brands = Brand.objects.filter(status=True)

    if search_query:
        brands = brands.filter(
            Q(brand_name__icontains=search_query) 
          
        )
    brands = brands.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="brands.csv"'
        writer = csv.writer(response)
        writer.writerow(["Brand Name"])
        for brand in brands:
            writer.writerow([
                brand.brand_name or "",
            ])
        return response

    paginator = Paginator(brands, 10)
    page_number = request.GET.get('page')
    brand_page = paginator.get_page(page_number)

    return render(request, "brand_list.html", {
        "brands": brand_page,
        "search_query": search_query
    })


@login_required
def brand_add(request):
    if request.method == "POST":
        form = BrandForm(request.POST)
        if form.is_valid():
            brand = form.save(commit=False)
            brand.created_by = request.user
            # brand.updated_by = request.user
            brand.save()
            messages.success(request, "Brand added successfully.")
            return redirect_with_company('brand_list')  # Redirect to a list or detail page after saving
            
    else:
        form = BrandForm()

    # return render(request, "add_brand.html", {"form": form})
    return render(request, 'add_brand.html', {'form': form, 'title': 'Add New Brand'})


@login_required
def edit_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == "POST":
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            brand = form.save(commit=False)
            # Preserve created_by, set updated_by to current user
            if not brand.created_by:
                brand.created_by = request.user
            brand.updated_by = request.user
            brand.save()
            messages.success(request, "Brand edited successfully.")
            return redirect_with_company('brand_list')  # Change redirect as per your flow
    else:
        form = BrandForm(instance=brand)

    # return render(request, "add_brand.html", {"form": form})
    return render(request, 'add_brand.html', {'form': form, 'title': 'Edit Brand'})

# Delete view
@require_POST
def delete_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    brand.status = False
    brand.save(update_fields=["status"])
    messages.success(request, "Brand deleted successfully.")
    return redirect_with_company('brand_list')
        