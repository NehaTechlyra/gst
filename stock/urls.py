from django.urls import path
from . import views
from .import_stock_views import (
    import_stock_step1,
    import_stock_step2,
    import_stock_step3,
    import_stock_sample,
)

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('add/', views.add_multiple_stock, name='add_multiple_stock'),
    path('stocks/<int:pk>/edit/', views.edit_stock, name='edit_stock'),
    path('stocks/delete/<int:pk>/', views.delete_stock, name='delete_stock'),
    path('item/<int:item_id>/detail/', views.stock_detail, name='stock_detail'),
    # Other URLs ...
    path('import_stock/',        import_stock_step1,  name='import_stock_step1'),
    path('import_stock/step2/',  import_stock_step2,  name='import_stock_step2'),
    path('import_stock/step3/',  import_stock_step3,  name='import_stock_step3'),
    path('import_stock/sample/', import_stock_sample, name='import_stock_sample'),
]