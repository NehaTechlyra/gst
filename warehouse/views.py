# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Warehouse
from .forms import WarehouseForm  
from django.core.paginator import Paginator
from django.db.models import Q,Sum, DecimalField, F
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models.functions import Coalesce
from stock.models import Stock
import csv
from decimal import Decimal, InvalidOperation



def warehouse_list(request):
    search_query = request.GET.get('q', '')
    warehouses = Warehouse.objects.filter(status=True)

    if search_query:
        warehouses = warehouses.filter(
            Q(warehouse_name__icontains=search_query) 
          
        )

    # 🔹 Annotate total stock per warehouse
    warehouses = warehouses.annotate(
        total_stock=Coalesce(
            Sum('warehouses__quantity', filter=Q(warehouses__item__status=True)),
            0,
            output_field=DecimalField(max_digits=15, decimal_places=2)
        )
    ).order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="warehouses.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Warehouse Name",
            "Code",
            "Address",
            "Contact Phone",
            "Contact Email",
            "Description",
            "Warehouse Incharge",
            "Is Default",
        ])
        for warehouse in warehouses:
            writer.writerow([
                warehouse.warehouse_name or "",
                warehouse.code or "",
                warehouse.address or "",
                warehouse.contact_phone or "",
                warehouse.contact_email or "",
                warehouse.description or "",
                warehouse.warehouse_incharge or "",
                "Yes" if warehouse.is_default else "No",
            ])
        return response

    # warehouses = warehouses.order_by('id')
    paginator = Paginator(warehouses, 10)
    page_number = request.GET.get('page')
    warehouse_page = paginator.get_page(page_number)

    return render(request, "warehouse_list.html", {
        "warehouses": warehouse_page,
        "search_query": search_query
    })


@login_required
def warehouse_add(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse.created_by = request.user
            # warehouse.updated_by = request.user
            warehouse.save()
            messages.success(request, "Warehouse added successfully.")
            return redirect_with_company('warehouse_list')  # Redirect to a list or detail page after saving
            
    else:
        form = WarehouseForm()

    # return render(request, "add_warehouse.html", {"form": form})
    return render(request, 'add_warehouse.html', {'form': form, 'title': 'Add New Warehouse'})


@login_required
def edit_warehouse(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)

    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            warehouse = form.save(commit=False)
            # Preserve created_by, set updated_by to current user
            if not warehouse.created_by:
                warehouse.created_by = request.user
            warehouse.updated_by = request.user
            warehouse.save()
            messages.success(request, "Warehouse edited successfully.")
            return redirect_with_company('warehouse_list')  # Change redirect as per your flow
    else:
        form = WarehouseForm(instance=warehouse)

    # return render(request, "add_warehouse.html", {"form": form})
    return render(request, 'add_warehouse.html', {'form': form, 'title': 'Edit Warehouse'})

# Delete view
@require_POST
def delete_warehouse(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    warehouse.status = False
    warehouse.save(update_fields=["status"])
    messages.success(request, "Warehouse deleted successfully.")
    return redirect_with_company('warehouse_list')

def warehouses_list(request):
    results = []
    # if query:
    warehouse = Warehouse.objects.filter(status=True)
    results = [{"id": h.id, "name": h.warehouse_name} for h in warehouse]
    return JsonResponse(results, safe=False)
        


def warehouse_detail(request, pk):
    """Render a simple readonly detail page for a order."""
    warehouse = get_object_or_404(Warehouse, pk=pk)

    # --- Stock table filters ---
    search_query = (request.GET.get('q') or '').strip()
    hide_zero_stock = request.GET.get('hide_zero') == '1'
    low_stock_only = request.GET.get('low_stock') == '1'
    threshold_raw = (request.GET.get('threshold') or '').strip()
    threshold_value = None
    if threshold_raw:
        try:
            threshold_value = Decimal(threshold_raw)
        except (InvalidOperation, ValueError):
            threshold_value = None

    stocks_qs = Stock.objects.filter(warehouse=warehouse, status=True, item__status=True)
    if search_query:
        stocks_qs = stocks_qs.filter(item__name__icontains=search_query)

    stocks = (
        stocks_qs
        .values('item__id', 'item__name', 'item__min_stock')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('item__name')
    )

    if hide_zero_stock:
        stocks = stocks.filter(total_quantity__gt=0)

    if low_stock_only:
        if threshold_value is not None:
            # Explicit threshold provided — applies to every item uniformly.
            stocks = stocks.filter(total_quantity__lte=threshold_value)
        else:
            # No explicit threshold — fall back to each item's own
            # "Minimum Stock Level" (Item.min_stock). Items without a
            # min_stock configured are excluded since there's nothing to
            # compare against.
            stocks = stocks.filter(
                item__min_stock__isnull=False,
                total_quantity__lte=F('item__min_stock'),
            )

    context = {
        'warehouse_form': WarehouseForm(instance=warehouse),
        # 'purchase_formset': purchase_formset,
        # 'all_items': Item.objects.all(),
        # 'today': localdate().isoformat(),
        # 'q_no': order.order_number,
        'warehouse': warehouse,
        'stocks': stocks,
        'search_query': search_query,
        'hide_zero_stock': hide_zero_stock,
        'low_stock_only': low_stock_only,
        'threshold_value': threshold_raw,
        'has_active_filters': bool(search_query or hide_zero_stock or low_stock_only),
        # 'subtotal_calc': subtotal_calc,
        # 'total_tax': total_tax,
        # 'total_cgst': total_cgst,
        # 'total_sgst': total_sgst,
        # 'total_item_discount': total_item_discount,
        # 'grand_discount': grand_discount,
        # 'grand_discount_value': grand_discount_value,
        # 'grand_discount_type': grand_discount_type,
        # 'final_total': final_total,
        # 'total_discount_combined': total_item_discount + grand_discount,
        
    }
    return render(request, 'warehouse_detail.html', context)
        