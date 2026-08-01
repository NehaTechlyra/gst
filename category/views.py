from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Category, Subcategory
from .forms import CategoryForm, SubcategoryForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
import csv

def category_list(request):
    search_query = request.GET.get('q', '')
    categories = Category.objects.filter(status=True)

    if search_query:
        categories = categories.filter(Q(category_name__icontains=search_query))

    categories = categories.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="categories.csv"'
        writer = csv.writer(response)
        writer.writerow(["Category Name"])
        for cat in categories:
            writer.writerow([
                cat.category_name or "",
            ])
        return response

    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    category_page = paginator.get_page(page_number)

    return render(request, "category_list.html", {"categories": category_page, "search_query": search_query})


def subcategory_list(request):
    search_query = request.GET.get('q', '')
    subcategories = Subcategory.objects.filter(status=True).select_related('category')

    if search_query:
        subcategories = subcategories.filter(
            Q(subcategory_name__icontains=search_query) |
            Q(category__category_name__icontains=search_query)
        )

    subcategories = subcategories.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="subcategories.csv"'
        writer = csv.writer(response)
        writer.writerow(["Subcategory Name", "Category"])
        for subcat in subcategories:
            writer.writerow([
                subcat.subcategory_name or "",
                subcat.category.category_name if subcat.category else "",
            ])
        return response

    paginator = Paginator(subcategories, 10)
    page_number = request.GET.get('page')
    subcategory_page = paginator.get_page(page_number)

    return render(request, "subcategory_list.html", {"subcategories": subcategory_page, "search_query": search_query})



@login_required
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.created_by = request.user
            cat.save()
            messages.success(request, "Category added successfully.")
            return redirect_with_company('category_list')
    else:
        form = CategoryForm()

    return render(request, 'add_category.html', {'form': form, 'title': 'Add New Category'})


@login_required
def add_subcategory(request):
    if request.method == "POST":
        form = SubcategoryForm(request.POST)
        if form.is_valid():
            subcat = form.save(commit=False)
            subcat.created_by = request.user
            subcat.save()
            messages.success(request, "Subcategory added successfully.")
            return redirect_with_company(request, 'subcategory_list')
    else:
        form = SubcategoryForm()

    return render(request, 'add_subcategory.html', {'form': form, 'title': 'Add New Subcategory'})


@login_required
def edit_category(request, pk):
    cat = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            cat = form.save(commit=False)
            if not cat.created_by:
                cat.created_by = request.user
            cat.updated_by = request.user
            cat.save()
            messages.success(request, "Category edited successfully.")
            return redirect_with_company('category_list')
    else:
        form = CategoryForm(instance=cat)

    return render(request, 'add_category.html', {'form': form, 'title': 'Edit Category'})


@login_required
def edit_subcategory(request, pk):
    subcat = get_object_or_404(Subcategory, pk=pk)

    if request.method == "POST":
        form = SubcategoryForm(request.POST, instance=subcat)
        if form.is_valid():
            subcat = form.save(commit=False)
            if not subcat.created_by:
                subcat.created_by = request.user
            subcat.updated_by = request.user
            subcat.save()
            messages.success(request, "Subcategory edited successfully.")
            return redirect_with_company(request, 'subcategory_list')
    else:
        form = SubcategoryForm(instance=subcat)

    return render(request, 'add_subcategory.html', {'form': form, 'title': 'Edit Subcategory'})


@require_POST
def delete_category(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    cat.status = False
    cat.save(update_fields=["status"])
    messages.success(request, "Category deleted successfully.")
    return redirect_with_company('category_list')


@require_POST
def delete_subcategory(request, pk):
    subcat = get_object_or_404(Subcategory, pk=pk)
    subcat.status = False
    subcat.save(update_fields=["status"])
    messages.success(request, "Subcategory deleted successfully.")
    return redirect_with_company(request, 'subcategory_list')
