from django.urls import path
from . import views
from . import customer_import_views

urlpatterns = [
    path('customers/', views.customer_list, name='customer_list'),

    path("customers/add/", views.add_customer, name="add_customers"),
    path('customers/<int:pk>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('generate-customer-code/', views.generate_customer_code, name='generate_customer_code'),

    # Other URLs ...

    path('import/step1/', customer_import_views.import_customers_step1, name='import_customers_step1'),
    path('import/step2/', customer_import_views.import_customers_step2, name='import_customers_step2'),
    path('import/step3/', customer_import_views.import_customers_step3, name='import_customers_step3'),
    path('import/sample/', customer_import_views.import_customers_sample, name='import_customers_sample'),
    path('export/csv/', customer_import_views.export_customers_csv, name='export_customers_csv'),
]
