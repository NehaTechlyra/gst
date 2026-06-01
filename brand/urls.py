from django.urls import path
from . import views
from .import_brand_views import (
    import_brand_step1,
    import_brand_step2,
    import_brand_step3,
    import_brand_sample,
)

urlpatterns = [
    path('brands/', views.brand_list, name='brand_list'),
    path('add/', views.brand_add, name='brand_add'),
    path('brands/<int:pk>/edit/', views.edit_brand, name='edit_brand'),
    path('brands/delete/<int:pk>/', views.delete_brand, name='delete_brand'),
    # Other URLs ...


    path('import_brand/',        import_brand_step1,  name='import_brand_step1'),
    path('import_brand/step2/',  import_brand_step2,  name='import_brand_step2'),
    path('import_brand/step3/',  import_brand_step3,  name='import_brand_step3'),
    path('import_brand/sample/', import_brand_sample, name='import_brand_sample'),
]
