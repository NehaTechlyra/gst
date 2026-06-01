from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import PriceList, PriceListItem, ContactPriceList
from .forms import PriceListForm, PriceListItemForm, ContactPriceListForm
from django.urls import reverse


# ─── Price List CRUD ──────────────────────────────────────────────────────────

def price_list_index(request):
    query = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    qs = PriceList.objects.prefetch_related('items', 'contact_assignments')

    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if type_filter:
        qs = qs.filter(type=type_filter)
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    return render(request, 'pricelist/index.html', {
        'price_lists': qs,
        'query': query,
        'type_filter': type_filter,
        'status_filter': status_filter,
    })


def price_list_create(request):
    form = PriceListForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        price_list = form.save()
        messages.success(request, f'Price list "{price_list.name}" created successfully.')
        url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list.pk})
        return redirect(url)
    return render(request, 'pricelist/form.html', {'form': form, 'title': 'Create Price List'})


def price_list_detail(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    items = price_list.items.all()  # Remove select_related for now
    assignments = price_list.contact_assignments.all()  # Remove select_related for now
    return render(request, 'pricelist/detail.html', {
        'price_list': price_list,
        'items': items,
        'assignments': assignments,
    })


def price_list_edit(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    form = PriceListForm(request.POST or None, instance=price_list)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Price list "{price_list.name}" updated.')
        url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': pk})
        return redirect(url)
    return render(request, 'pricelist/form.html', {
        'form': form,
        'title': f'Edit — {price_list.name}',
        'price_list': price_list,
    })


def price_list_delete(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        name = price_list.name
        price_list.delete()
        messages.success(request, f'Price list "{name}" deleted.')
        url = reverse('pricelist:price_list_index', kwargs={'company_code': request.company_code})
        return redirect(url)
    return render(request, 'pricelist/confirm_delete.html', {'price_list': price_list})


def price_list_toggle_status(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    price_list.is_active = not price_list.is_active
    price_list.save(update_fields=['is_active'])
    status = 'activated' if price_list.is_active else 'deactivated'
    messages.success(request, f'Price list "{price_list.name}" {status}.')
    url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': pk})
    return redirect(url)


# ─── Price List Items ─────────────────────────────────────────────────────────

def price_list_item_add(request, price_list_pk):
    price_list = get_object_or_404(PriceList, pk=price_list_pk)
    form = PriceListItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.price_list = price_list
        item.save()
        messages.success(request, 'Item added to price list.')
        url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list_pk})
        return redirect(url)
    return render(request, 'pricelist/item_form.html', {
        'form': form,
        'price_list': price_list,
        'title': 'Add Item',
    })


def price_list_item_edit(request, price_list_pk, item_pk):
    price_list = get_object_or_404(PriceList, pk=price_list_pk)
    pl_item = get_object_or_404(PriceListItem, pk=item_pk, price_list=price_list)
    form = PriceListItemForm(request.POST or None, instance=pl_item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Item updated.')
        url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list_pk})
        return redirect(url)
    return render(request, 'pricelist/item_form.html', {
        'form': form,
        'price_list': price_list,
        'title': 'Edit Item',
    })


def price_list_item_delete(request, price_list_pk, item_pk):
    pl_item = get_object_or_404(PriceListItem, pk=item_pk, price_list_id=price_list_pk)
    pl_item.delete()
    messages.success(request, 'Item removed from price list.')
    url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list_pk})
    return redirect(url)


# ─── Contact Assignment ───────────────────────────────────────────────────────

def contact_price_list_assign(request, price_list_pk):
    price_list = get_object_or_404(PriceList, pk=price_list_pk)
    form = ContactPriceListForm(request.POST or None, initial={'price_list': price_list})
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.price_list = price_list
        assignment.save()
        messages.success(request, 'Contact assigned to price list.')
        url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list_pk})
        return redirect(url)
    return render(request, 'pricelist/assign_contact.html', {
        'form': form,
        'price_list': price_list,
    })


def contact_price_list_remove(request, price_list_pk, assignment_pk):
    assignment = get_object_or_404(ContactPriceList, pk=assignment_pk, price_list_id=price_list_pk)
    assignment.delete()
    messages.success(request, 'Contact removed from price list.')
    url = reverse('pricelist:price_list_detail', kwargs={'company_code': request.company_code, 'pk': price_list_pk})
    return redirect(url)


# ─── Utility: Get price for item from active contact price list ───────────────

def get_price_for_contact(contact, item):
    """
    Call this utility in your invoice/sales order views to auto-apply
    the correct price list rate for a given contact + item combo.
    Returns the computed price or the item's base rate as fallback.
    """
    assignment = ContactPriceList.objects.filter(
        contact=contact,
        price_list__is_active=True
    ).select_related('price_list').first()

    if assignment:
        try:
            pl_item = PriceListItem.objects.get(
                price_list=assignment.price_list,
                item=item
            )
            return pl_item.get_computed_price()
        except PriceListItem.DoesNotExist:
            pass

    return item.rate  # fallback to base rate
