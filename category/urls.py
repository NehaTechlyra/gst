from django.urls import path
from . import views
from .import_category_views import (
    import_category_step1,
    import_category_step2,
    import_category_step3,
    import_category_sample,
)

urlpatterns = [
    path('categories/', views.category_list, name='category_list'),
    path('add/', views.add_category, name='category_add'),
    path('categories/<int:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('subcategories/', views.subcategory_list, name='subcategory_list'),
    path('subcategories/add/', views.add_subcategory, name='subcategory_add'),
    path('subcategories/<int:pk>/edit/', views.edit_subcategory, name='edit_subcategory'),
    path('subcategories/delete/<int:pk>/', views.delete_subcategory, name='delete_subcategory'),

    path('import_category/step1/', import_category_step1, name='import_category_step1'),
    path('import_category/step2/', import_category_step2, name='import_category_step2'),
    path('import_category/step3/', import_category_step3, name='import_category_step3'),
    path('import_category/sample/', import_category_sample, name='import_category_sample'),
]
