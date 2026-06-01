from django.urls import path
from . import views
from .import_type_views import (
    import_type_step1,
    import_type_step2,
    import_type_step3,
    import_type_sample,
)

urlpatterns = [
    path('types/', views.type_list, name='type_list'),
    path('add/', views.add_type, name='type_add'),
    path('types/<int:pk>/edit/', views.edit_type, name='edit_type'),
    path('types/delete/<int:pk>/', views.delete_type, name='delete_type'),

    path('import_type/step1/', import_type_step1, name='import_type_step1'),
    path('import_type/step2/', import_type_step2, name='import_type_step2'),
    path('import_type/step3/', import_type_step3, name='import_type_step3'),
    path('import_type/sample/', import_type_sample, name='import_type_sample'),
]
