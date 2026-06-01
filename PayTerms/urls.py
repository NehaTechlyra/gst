from django.urls import path
from . import views
from .import_payterm_views import (
    import_payterm_step1,
    import_payterm_step2,
    import_payterm_step3,
    import_payterm_sample,
)

urlpatterns = [
        path('payterm/', views.payterm_view, name='payterm_view'),
        path('payterm_list/', views.payterm_list, name='payterm_list'),
        path('save_payterms/', views.save_payterms, name='save_payterms'),
        path('add/', views.payterm_add, name='payterm_add'),
        path('payterms/<int:pk>/edit/', views.edit_payterm, name='edit_payterm'),
        path('payterms/delete/<int:pk>/', views.delete_payterm, name='delete_payterm'),
        path('import_payterm/',        import_payterm_step1,  name='import_payterm_step1'),
        path('import_payterm/step2/',  import_payterm_step2,  name='import_payterm_step2'),
        path('import_payterm/step3/',  import_payterm_step3,  name='import_payterm_step3'),
        path('import_payterm/sample/', import_payterm_sample, name='import_payterm_sample'),
]