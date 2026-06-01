from django.urls import path

from Items import import_views
from . import views
from .views import check_barcode_unique

urlpatterns = [
    # path('', views.items_list, name='items_list'),
                path('', views.items, name='items'),

    path('add_item/', views.add_item, name='add_item'),
    path('items/delete/<int:pk>/', views.delete_item, name='delete_item'),
    path('<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('hsn-codes/', views.hsn_code_search, name='hsn_code_search'),
    path('get-item-hsn/', views.get_item_hsn, name='get_item_hsn'),
    path('sac-codes/', views.sac_code_search, name='sac_code_search'),
    path('uom/', views.unit_search, name='unit_search'),
    path('unit/', views.search_unit, name='search_unit'),
    path('brand/', views.brand_search, name='brand_search'),
    path('category/', views.category_search, name='category_search'),
    path('item-type/', views.item_type_search, name='item_type_search'),
    path('warehouse/', views.warehouse_search, name='warehouse_search'),
    path('vendor/', views.vendor_search, name='vendor_search'),
    path('uom_search/', views.uom_search, name='uom_search'),
    path('uom_createform/', views.create_uom_ajax, name='create_uom_ajax'),
    path('unit_createform/', views.create_unit_ajax, name='create_unit_ajax'),
    path('add_unit/', views.add_unit, name='add_unit'),
    path('add_uom/', views.add_uom, name='add_uom'),
    path('add_brand/', views.add_brand, name='add_brand'),
    path('add_category/', views.add_category, name='add_category'),
    path('add_item_type/', views.add_item_type, name='add_item_type'),
    path('add_warehouse/', views.add_warehouse, name='add_warehouse'),
    path('brand_createform/', views.create_brand_ajax, name='create_brand_ajax'),
    path('category_createform/', views.create_category_ajax, name='create_category_ajax'),
    path('item_type_createform/', views.create_item_type_ajax, name='create_item_type_ajax'),
    path('warehouse_createform/', views.create_warehouse_ajax, name='create_warehouse_ajax'),
    path('vendor_createform/', views.create_vendor_ajax, name='create_vendor_ajax'),
    path('add_vendor/', views.add_vendor, name='add_vendor'),
    path('tax-groups/', views.tax_group_search, name='tax_group_search'),
    # path('get-uoms/', views.get_uoms, name='get_uoms'),
    path('inter-state-taxes/', views.inter_state_tax_list, name='inter_state_tax_list'),
    path('check_barcode_unique/', check_barcode_unique, name='check_barcode_unique'),
    path('create-item-ajax/', views.create_item_ajax, name='create_item_ajax'),

    path('create-item-ajax-sales/', views.create_item_ajax_sales, name='create_item_ajax_sales'),


    path('import/',        import_views.import_items_step1,  name='import_items_step1'),
    path('import/step2/',  import_views.import_items_step2,  name='import_items_step2'),
    path('import/step3/',  import_views.import_items_step3,  name='import_items_step3'),
    path('import/sample/', import_views.import_items_sample, name='import_items_sample'),






]
