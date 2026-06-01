from django.urls import path
from . import views

app_name = 'pricelists'

urlpatterns = [
    # Price List CRUD
    path('', views.price_list_index, name='index'),
    path('create/', views.price_list_create, name='create'),
    path('<int:pk>/', views.price_list_detail, name='detail'),
    path('<int:pk>/edit/', views.price_list_edit, name='edit'),
    path('<int:pk>/delete/', views.price_list_delete, name='delete'),
    path('<int:pk>/toggle-status/', views.price_list_toggle_status, name='toggle_status'),
    path('<int:pk>/duplicate/', views.price_list_duplicate, name='duplicate'),
    path('<int:pk>/export-csv/', views.price_list_export_csv, name='export_csv'),

    # Price List Item API (AJAX)
    path('<int:price_list_pk>/items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/update/', views.item_update, name='item_update'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),

    # Utility API
    path('api/item-price/', views.get_item_price, name='get_item_price'),

    # Assignment
    path('<int:pk>/assign/', views.assign_contacts, name='assign_contacts'),
]
