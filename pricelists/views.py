from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
import json
import csv
from django.http import HttpResponse

from .models import PriceList, PriceListItem, ContactPriceList
from .forms import PriceListForm, PriceListItemForm
from Items.models import Item
from customer.models import Customer
from Purchase.models import Vendor
from decimal import Decimal
from django.db import transaction


# ─────────────────────────────────────────────
#  PRICE LIST VIEWS
# ─────────────────────────────────────────────

def price_list_index(request):
    """List all price lists with search & filter."""
    query = request.GET.get('q', '')
    price_type = request.GET.get('type', '')
    status = request.GET.get('status', '')

    qs = PriceList.objects.annotate(item_count=Count('price_list_items'))

    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if price_type:
        qs = qs.filter(price_type=price_type)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'price_type': price_type,
        'status': status,
        'total_count': qs.count(),
        'active_count': PriceList.objects.filter(is_active=True).count(),
        'sales_count': PriceList.objects.filter(price_type='sales').count(),
        'purchase_count': PriceList.objects.filter(price_type='purchase').count(),
    }
    return render(request, 'pricelists/index.html', context)


def _save_individual_items(request, price_list):
    """Helper to save individual item rates from POST data."""
    if price_list.pricing_scheme != 'individual':
        return
    
    # We expect item rates in the format item_rate_<item_id>
    for key, value in request.POST.items():
        if key.startswith('item_rate_') and value:
            try:
                item_id = int(key.replace('item_rate_', ''))
                rate = Decimal(value)
                item_obj = Item.objects.get(pk=item_id)
                
                # Determine the base price (standard rate)
                base_price = item_obj.selling_price if price_list.price_type == 'sales' else (item_obj.cost_price or 0)
                
                # Check if PriceListItem already exists
                PriceListItem.objects.update_or_create(
                    price_list=price_list,
                    item_sku=item_obj.barcode or item_obj.name,  # Using SKU as identifier
                    defaults={
                        'item_name': item_obj.name,
                        'unit': item_obj.unit,
                        'base_price': base_price or 0,
                        'discount_type': 'custom',  # ✅ Must be 'custom' for final_price to use custom_price
                        'discount_value': 0,
                        'custom_price': rate,
                    }
                )
            except (ValueError, Item.DoesNotExist):
                continue

def price_list_create(request):
    """Create a new price list."""
    items = Item.objects.filter(status=True)
    if request.method == 'POST':
        form = PriceListForm(request.POST)
        if form.is_valid():
            price_list = form.save()
            _save_individual_items(request, price_list)
            messages.success(request, f'Price list "{price_list.name}" created successfully.')
            return redirect('pricelists:detail', company_code=request.company_code, pk=price_list.pk)
    else:
        form = PriceListForm()

    return render(request, 'pricelists/form.html', {
        'form': form, 
        'action': 'Create',
        'items': items,
        'existing_items': {}
    })


def price_list_detail(request, pk):
    """View a price list and its items."""
    price_list = get_object_or_404(PriceList, pk=pk)
    items = price_list.price_list_items.all()
    item_form = PriceListItemForm()

    query = request.GET.get('q', '')
    if query:
        items = items.filter(
            Q(item_name__icontains=query) | Q(item_sku__icontains=query)
        )

    paginator = Paginator(items, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'price_list': price_list,
        'page_obj': page_obj,
        'item_form': item_form,
        'query': query,
        'item_count': price_list.price_list_items.count(),
    }
    return render(request, 'pricelists/detail.html', context)


def price_list_edit(request, pk):
    """Edit a price list."""
    price_list = get_object_or_404(PriceList, pk=pk)
    items = Item.objects.filter(status=True)
    
    # Get existing item rates for this price list
    existing_items = {
        item.item_sku: item.custom_price 
        for item in price_list.price_list_items.all()
    }
    
    if request.method == 'POST':
        form = PriceListForm(request.POST, instance=price_list)
        if form.is_valid():
            form.save()
            _save_individual_items(request, price_list)
            messages.success(request, f'Price list "{price_list.name}" updated successfully.')
            return redirect('pricelists:detail', company_code=request.company_code, pk=price_list.pk)
    else:
        form = PriceListForm(instance=price_list)

    return render(request, 'pricelists/form.html', {
        'form': form, 
        'action': 'Edit', 
        'price_list': price_list,
        'items': items,
        'existing_items': existing_items
    })


def price_list_delete(request, pk):
    """Delete a price list."""
    price_list = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        name = price_list.name
        price_list.delete()
        messages.success(request, f'Price list "{name}" deleted.')
        return redirect('pricelists:index', company_code=request.company_code)
    return render(request, 'pricelists/confirm_delete.html', {'price_list': price_list})


def price_list_toggle_status(request, pk):
    """Toggle active/inactive status via AJAX."""
    price_list = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        price_list.is_active = not price_list.is_active
        price_list.save()
        return JsonResponse({
            'success': True,
            'is_active': price_list.is_active,
            'message': f'Price list {"activated" if price_list.is_active else "deactivated"}.'
        })
    return JsonResponse({'success': False}, status=400)


def price_list_duplicate(request, pk):
    """Duplicate a price list with all its items."""
    original = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        new_pl = PriceList.objects.create(
            name=f"Copy of {original.name}",
            price_type=original.price_type,
            pricing_scheme=original.pricing_scheme,
            percentage_value=original.percentage_value,
            percentage_type=original.percentage_type,
            currency=original.currency,
            description=original.description,
            rounding=original.rounding,
            is_active=False,
        )
        for item in original.price_list_items.all():
            PriceListItem.objects.create(
                price_list=new_pl,
                item_name=item.item_name,
                item_sku=item.item_sku,
                unit=item.unit,
                base_price=item.base_price,
                discount_type=item.discount_type,
                discount_value=item.discount_value,
                custom_price=item.custom_price,
                min_quantity=item.min_quantity,
                max_quantity=item.max_quantity,
            )
        messages.success(request, f'Price list duplicated as "Copy of {original.name}".')
        return redirect('pricelists:detail', company_code=request.company_code, pk=new_pl.pk)
    return JsonResponse({'success': False}, status=400)


def price_list_export_csv(request, pk):
    """Export price list items as CSV."""
    price_list = get_object_or_404(PriceList, pk=pk)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{price_list.name}_pricelist.csv"'

    writer = csv.writer(response)
    writer.writerow(['Item Name', 'SKU', 'Unit', 'Base Price', 'Discount Type',
                     'Discount Value', 'Final Price', 'Min Quantity'])
    for item in price_list.price_list_items.all():
        writer.writerow([
            item.item_name, item.item_sku or '', item.unit or '',
            item.base_price, item.get_discount_type_display(),
            item.discount_value, item.final_price, item.min_quantity
        ])
    return response


# ─────────────────────────────────────────────
#  PRICE LIST ITEM API (AJAX)
# ─────────────────────────────────────────────

@require_http_methods(["POST"])
def item_create(request, price_list_pk):
    """Add item to a price list via AJAX."""
    price_list = get_object_or_404(PriceList, pk=price_list_pk)
    data = json.loads(request.body)
    form = PriceListItemForm(data)
    if form.is_valid():
        item = form.save(commit=False)
        item.price_list = price_list
        item.save()
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'item_name': item.item_name,
                'item_sku': item.item_sku or '',
                'unit': item.unit or '',
                'base_price': str(item.base_price),
                'discount_type': item.get_discount_type_display(),
                'discount_value': str(item.discount_value),
                'final_price': str(item.final_price),
                'min_quantity': item.min_quantity,
            }
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_http_methods(["PUT"])
def item_update(request, pk):
    """Update a price list item via AJAX."""
    item = get_object_or_404(PriceListItem, pk=pk)
    data = json.loads(request.body)
    form = PriceListItemForm(data, instance=item)
    if form.is_valid():
        item = form.save()
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'item_name': item.item_name,
                'item_sku': item.item_sku or '',
                'unit': item.unit or '',
                'base_price': str(item.base_price),
                'discount_type': item.get_discount_type_display(),
                'discount_value': str(item.discount_value),
                'final_price': str(item.final_price),
                'min_quantity': item.min_quantity,
            }
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_http_methods(["DELETE"])
def item_delete(request, pk):
    """Delete a price list item via AJAX."""
    item = get_object_or_404(PriceListItem, pk=pk)
    item.delete()
    return JsonResponse({'success': True})


def get_item_price(request):
    """Get the price of an item from a specific price list (for transaction use)."""
    price_list_id = request.GET.get('price_list_id')
    item_sku = request.GET.get('item_sku')
    quantity = request.GET.get('quantity', 1)

    if not price_list_id or not item_sku:
        return JsonResponse({'error': 'price_list_id and item_sku required'}, status=400)
    
    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1
        
    try:
        price_list = PriceList.objects.get(pk=price_list_id)
    except PriceList.DoesNotExist:
        return JsonResponse({'error': 'Price list not found'}, status=404)

    # First check for individual item override or if scheme is individual
    qs = PriceListItem.objects.filter(price_list_id=price_list_id, item_sku=item_sku, min_quantity__lte=quantity)
    item = None
    for p_item in qs.order_by('-min_quantity'):
        if p_item.max_quantity is None or p_item.max_quantity >= quantity:
            item = p_item
            break

    if item:
        assert item is not None
        return JsonResponse({
            'success': True,
            'item_name': item.item_name,
            'base_price': str(item.base_price),
            'final_price': str(item.final_price),
            'discount_type': item.discount_type,
            'discount_value': str(item.discount_value),
            'min_quantity': item.min_quantity,
            'max_quantity': item.max_quantity,
        })
        
    if price_list.pricing_scheme == 'percentage':
        # Fallback to computing from the Items catalog
        try:
            from Items.models import Item
            from decimal import Decimal
            import math
            
            # Using name or main_barcode
            item_obj = Item.objects.filter(Q(name=item_sku) | Q(main_barcode__barcode=item_sku)).first()
            if item_obj:
                base_price = item_obj.selling_price if price_list.price_type == 'sales' else item_obj.cost_price
                if base_price is None:
                    base_price = Decimal('0.00')
                    
                percentage = price_list.percentage_value or Decimal('0.00')
                discount_amount = base_price * (percentage / Decimal('100.00'))
                
                if price_list.percentage_type == 'markup':
                    final_price = base_price + discount_amount
                else: # markdown
                    final_price = base_price - discount_amount
                    
                # Handle rounding
                if price_list.rounding == 'nearest':
                    final_price = Decimal(round(float(final_price)))
                elif price_list.rounding == 'up':
                    final_price = Decimal(math.ceil(float(final_price)))
                elif price_list.rounding == 'down':
                    final_price = Decimal(math.floor(float(final_price)))
                else:
                    final_price = final_price.quantize(Decimal('0.01'))
                    
                return JsonResponse({
                    'success': True,
                    'item_name': item_obj.name,
                    'base_price': str(base_price),
                    'final_price': str(final_price),
                    'discount_type': 'percentage_scheme',
                    'discount_value': str(percentage),
                    'min_quantity': 1,
                    'max_quantity': None,
                })
        except Exception as e:
            pass
            
    return JsonResponse({'success': False, 'error': 'Item not found in this price list or catalog'}, status=404)

def assign_contacts(request, pk):
    """View to assign price list to customers and vendors."""
    price_list = get_object_or_404(PriceList, pk=pk)
    
    if request.method == 'POST':
        customer_ids = request.POST.getlist('customers')
        vendor_ids = request.POST.getlist('vendors')
        
        with transaction.atomic():
            # Clear this price list from all customers it was assigned to
            if price_list.price_type == 'sales':
                Customer.objects.filter(sales_price_list=price_list).update(sales_price_list=None)
                Vendor.objects.filter(sales_price_list=price_list).update(sales_price_list=None)
                
                # Assign to selected customers
                Customer.objects.filter(id__in=customer_ids).update(sales_price_list=price_list)
                # Assign to selected vendors (who might also be sales targets)
                Vendor.objects.filter(id__in=vendor_ids).update(sales_price_list=price_list)
                
            else: # purchase
                Customer.objects.filter(purchase_price_list=price_list).update(purchase_price_list=None)
                Vendor.objects.filter(purchase_price_list=price_list).update(purchase_price_list=None)
                
                # Assign to selected customers (who might also be vendors)
                Customer.objects.filter(id__in=customer_ids).update(purchase_price_list=price_list)
                # Assign to selected vendors
                Vendor.objects.filter(id__in=vendor_ids).update(purchase_price_list=price_list)
                
        messages.success(request, f'Price list "{price_list.name}" assigned successfully.')
        return redirect('pricelists:detail', company_code=request.company_code, pk=pk)

    # For display
    customers = Customer.objects.all().order_by('first_name', 'company_name')
    vendors = Vendor.objects.all().order_by('first_name', 'company_name')
    
    # Get currently assigned IDs
    if price_list.price_type == 'sales':
        assigned_customer_ids = list(Customer.objects.filter(sales_price_list=price_list).values_list('id', flat=True))
        assigned_vendor_ids = list(Vendor.objects.filter(sales_price_list=price_list).values_list('id', flat=True))
    else:
        assigned_customer_ids = list(Customer.objects.filter(purchase_price_list=price_list).values_list('id', flat=True))
        assigned_vendor_ids = list(Vendor.objects.filter(purchase_price_list=price_list).values_list('id', flat=True))

    context = {
        'price_list': price_list,
        'customers': customers,
        'vendors': vendors,
        'assigned_customer_ids': assigned_customer_ids,
        'assigned_vendor_ids': assigned_vendor_ids,
    }
    return render(request, 'pricelists/assign_contacts.html', context)
