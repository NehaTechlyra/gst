from django.urls import path
from . import views
from .import_warehouse_views import (
    import_warehouse_step1,
    import_warehouse_step2,
    import_warehouse_step3,
    import_warehouse_sample,
)

urlpatterns = [
    path('', views.warehouse_list, name='warehouse_list'),
    path('add/', views.warehouse_add, name='warehouse_add'),
    path('warehouses/<int:pk>/edit/', views.edit_warehouse, name='edit_warehouse'),
    path('warehouses/delete/<int:pk>/', views.delete_warehouse, name='delete_warehouse'),
    path('warehouses_list/', views.warehouses_list, name='warehouses_list'),
    path('/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    # Other URLs ...
    path('import_warehouse/',        import_warehouse_step1,  name='import_warehouse_step1'),
    path('import_warehouse/step2/',  import_warehouse_step2,  name='import_warehouse_step2'),
    path('import_warehouse/step3/',  import_warehouse_step3,  name='import_warehouse_step3'),
    path('import_warehouse/sample/', import_warehouse_sample, name='import_warehouse_sample'),
]