import json

from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Max
from django.contrib import messages
from user.utils import has_permission
from Lyraerp.utils.redirect_utils import redirect_with_company
from company.models import Company
from Items.models import Item
from customer.models import Customer
from Purchase.models import Vendor
from warehouse.models import Warehouse
from brand.models import Brand
from category.models import Category
from stock.models import Stock
from Tax.models import Tax
from type.models import Type
from unit.models import Unit
from user.models import Role
from PayTerms.models import PayTerms
from Items.permissions import can_view_items
from sales.permissions import can_view_customers
from Purchase.permissions import can_view_vendors
from warehouse.permissions import can_view_warehouse
from stock.permissions import can_view_stock
from Tax.permissions import can_view_taxes
from brand.permissions import can_view_brands
from category.permissions import can_view_categories
from type.permissions import can_view_types
from unit.permissions import can_view_units
from user.permissions import (
    can_view_users as can_view_users_perm,
    can_view_user_roles as can_view_user_roles_perm,
)
from PayTerms.permissions import can_view_payterms

@login_required
def masters_dashboard(request):
    """Render a small masters dashboard with basic counts."""
    try:
        has_dashboard_access = (
            getattr(request.user, 'is_superuser', False)
            or has_permission(request.user, 'Masters Dashboard', 'View')
            
        )
        if not has_dashboard_access:
            messages.error(request, 'You do not have permission to view Masters Dashboard.')
            return redirect_with_company('index')
    except Exception:
        messages.error(request, 'You do not have permission to view Masters Dashboard.')
        return redirect_with_company('index')
    company_db = getattr(request, 'company_db', 'default')

    # Permission flags to show/hide individual overview cards
    can_view_items_flag = can_view_items(request.user)
    can_view_customers_flag = can_view_customers(request.user)
    can_view_vendors_flag = can_view_vendors(request.user)
    can_view_warehouse_flag = can_view_warehouse(request.user)
    can_view_stock_flag = can_view_stock(request.user)
    can_view_users_flag = can_view_users_perm(request.user)

    can_view_payment_terms = can_view_payterms(request.user)
    can_view_user_roles = can_view_user_roles_perm(request.user)

    can_view_taxes_flag = can_view_taxes(request.user)
    can_view_brands_flag = can_view_brands(request.user)
    can_view_categories_flag = can_view_categories(request.user)
    can_view_types_flag = can_view_types(request.user)
    can_view_units_flag = can_view_units(request.user)

    user_model = get_user_model()
    try:
        company_count = Company.objects.count()
    except Exception:
        company_count = 0

    try:
        item_count = Item.objects.using(company_db).filter(status=True).count()
    except Exception:
        item_count = 0

    try:
        customer_count = Customer.objects.using(company_db).count()
    except Exception:
        customer_count = 0

    try:
        vendor_count = Vendor.objects.using(company_db).filter(is_active=True).count()
    except Exception:
        vendor_count = 0

    try:
        warehouse_count = Warehouse.objects.using(company_db).count()
    except Exception:
        warehouse_count = 0

    try:
        brand_count = Brand.objects.using(company_db).count()
    except Exception:
        brand_count = 0

    try:
        category_count = Category.objects.using(company_db).count()
    except Exception:
        category_count = 0

    try:
        brand_items_qs = (
            Brand.objects.using(company_db)
            .annotate(item_count=Count('items'))
            .order_by('-item_count')
        )
        max_brand_items = brand_items_qs.aggregate(max_count=Max('item_count'))['max_count'] or 1
        top_brands = []
        for brand in brand_items_qs[:6]:
            pct = round((brand.item_count / max_brand_items) * 100) if max_brand_items else 0
            top_brands.append({
                'brand_name': brand.brand_name or 'Unnamed',
                'item_count': brand.item_count,
                'pct': pct,
            })
    except Exception:
        top_brands = []

    try:
        category_items_qs = (
            Category.objects.using(company_db)
            .annotate(item_count=Count('items'))
            .order_by('-item_count')
        )
        max_cat_items = category_items_qs.aggregate(max_count=Max('item_count'))['max_count'] or 1
        top_categories = []
        for cat in category_items_qs[:6]:
            pct = round((cat.item_count / max_cat_items) * 100) if max_cat_items else 0
            top_categories.append({
                'category_name': cat.category_name or 'Uncategorized',
                'item_count': cat.item_count,
                'pct': pct,
            })
    except Exception:
        top_categories = []

    try:
        product_count = Item.objects.using(company_db).filter(type='goods').count()
        service_count = Item.objects.using(company_db).filter(type='service').count()
        raw_material_count = Item.objects.using(company_db).filter(
            Q(type__iexact='raw') | Q(item_type__type_name__icontains='raw')
        ).count()
    except Exception:
        product_count = service_count = raw_material_count = 0

    try:
        stock_total = Stock.objects.using(company_db).aggregate(total=Sum('quantity'))['total'] or 0
        stock_count = float(stock_total)
    except Exception:
        stock_count = 0

    try:
        user_count = user_model.objects.using(company_db).count()
    except Exception:
        user_count = 0

    try:
        role_count = Role.objects.using(company_db).count()
    except Exception:
        role_count = 0

    try:
        payterm_count = PayTerms.objects.using(company_db).filter(is_active=True).count()
    except Exception:
        payterm_count = 0

    try:
        tax_count = Tax.objects.using(company_db).count()
    except Exception:
        tax_count = 0

    try:
        type_count = Type.objects.using(company_db).count()
    except Exception:
        type_count = 0

    try:
        unit_count = Unit.objects.using(company_db).count()
    except Exception:
        unit_count = 0

    try:
        tax_qs = Tax.objects.using(company_db).filter(status=True).order_by('taxname')
        tax_list = list(tax_qs)
        individual_taxes = tax_qs.count()
    except Exception:
        tax_list = []
        individual_taxes = 0

    try:
        recent_customers = Customer.objects.using(company_db).filter(is_active=True).order_by('-created_at')[:6]
    except Exception:
        recent_customers = []

    try:
        recent_vendors = Vendor.objects.using(company_db).filter(is_active=True).order_by('-created_at')[:6]
    except Exception:
        recent_vendors = []

    try:
        warehouse_stock_qs = (
            Stock.objects.using(company_db)
            .values('warehouse__warehouse_name')
            .annotate(total=Sum('quantity'))
            .order_by('-total')
        )
        warehouse_stock = [
            {
                'warehouse__warehouse_name': entry['warehouse__warehouse_name'],
                'total': float(entry['total'] or 0)
            }
            for entry in warehouse_stock_qs
        ]
    except Exception:
        warehouse_stock = []
    warehouse_stock_json = json.dumps(warehouse_stock)

    try:
        items_by_cat_qs = (
            Category.objects.using(company_db)
            .annotate(item_total=Count('items'))
            .filter(item_total__gt=0)
            .order_by('-item_total')
        )
        items_by_cat_labels = [cat.category_name or "Uncategorized" for cat in items_by_cat_qs]
        items_by_cat_data = [cat.item_total for cat in items_by_cat_qs]
    except Exception:
        items_by_cat_labels = []
        items_by_cat_data = []
    items_by_cat_labels = json.dumps(items_by_cat_labels)
    items_by_cat_data = json.dumps(items_by_cat_data)

    context = {
        'company_count': company_count,
        'item_count': item_count,
        'customer_count': customer_count,
        'vendor_count': vendor_count,
        'warehouse_count': warehouse_count,
        'brand_count': brand_count,
        'category_count': category_count,
        'product_count': product_count,
        'service_count': service_count,
        'raw_material_count': raw_material_count,
        'stock_count': stock_count,
        'user_count': user_count,
        'role_count': role_count,
        'payterm_count': payterm_count,
        'can_view_payment_terms': can_view_payment_terms,
        'can_view_user_roles': can_view_user_roles,
        'can_view_items': can_view_items_flag,
        'can_view_customers': can_view_customers_flag,
        'can_view_vendors': can_view_vendors_flag,
        'can_view_warehouse': can_view_warehouse_flag,
        'can_view_stock': can_view_stock_flag,
        'can_view_users': can_view_users_flag,
        'can_view_taxes': can_view_taxes_flag,
        'can_view_brands': can_view_brands_flag,
        'can_view_categories': can_view_categories_flag,
        'can_view_types': can_view_types_flag,
        'can_view_units': can_view_units_flag,
        'tax_count': tax_count,
        'type_count': type_count,
        'unit_count': unit_count,
        'recent_customers': recent_customers,
        'recent_vendors': recent_vendors,
        'warehouse_stock': warehouse_stock,
        'warehouse_stock_json': warehouse_stock_json,
        'items_by_cat_labels': items_by_cat_labels,
        'items_by_cat_data': items_by_cat_data,
        'top_brands': top_brands,
        'top_categories': top_categories,
        'tax_list': tax_list,
        'individual_taxes': individual_taxes,
    }
    return render(request, 'masters/masters_dashboard.html', context)
