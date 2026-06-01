from django.urls import path
from . import views

app_name = 'pricelist'

urlpatterns = [
    # Price Lists
    path('', views.price_list_index, name='price_list_index'),
    path('create/', views.price_list_create, name='price_list_create'),
    path('<int:pk>/', views.price_list_detail, name='price_list_detail'),
    path('<int:pk>/edit/', views.price_list_edit, name='price_list_edit'),
    path('<int:pk>/delete/', views.price_list_delete, name='price_list_delete'),
    path('<int:pk>/toggle-status/', views.price_list_toggle_status, name='price_list_toggle_status'),

    # Price List Items
    path('<int:price_list_pk>/items/add/', views.price_list_item_add, name='price_list_item_create'),
    path('<int:price_list_pk>/items/<int:item_pk>/edit/', views.price_list_item_edit, name='price_list_item_edit'),
    path('<int:price_list_pk>/items/<int:item_pk>/delete/', views.price_list_item_delete, name='price_list_item_delete'),

    # Contact Assignments
    path('<int:price_list_pk>/assign-contact/', views.contact_price_list_assign, name='contact_assignment_create'),
    path('<int:price_list_pk>/remove-contact/<int:assignment_pk>/', views.contact_price_list_remove, name='contact_assignment_remove'),
]
