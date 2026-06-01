from django.urls import path

from . import views

urlpatterns = [
    path('', views.create_purchase_order, name='create_purchase_order'),  # e.g., default view for module
    # ... other purchase module URLs
            path('pur_trial/', views.pur, name='pur'),
            path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='supplier_add'),
     path('get-vendor/<int:vendor_id>/', views.get_vendor, name='get_vendor'),
    path('get-item/<int:item_id>/', views.get_item, name='get_item'),

     path('add-items/<int:po_id>/', views.add_purchase_order_items, name='add_purchase_order_items'),
]