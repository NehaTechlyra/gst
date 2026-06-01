from django.urls import path
from . import views
from .import_unit_views import (
    import_unit_step1,
    import_unit_step2,
    import_unit_step3,
    import_unit_sample,
)


urlpatterns = [
    path('units/', views.unit_list, name='unit_list'),
    path("units/add/", views.add_unit, name="items_add_unit"),
    path('units/<int:pk>/edit/', views.edit_unit, name='edit_unit'),
    path('units/delete/<int:pk>/', views.delete_unit, name='delete_unit'),
    # Other URLs ...

    path('import_unit/step1/', import_unit_step1, name='import_unit_step1'),
    path('import_unit/step2/', import_unit_step2, name='import_unit_step2'),
    path('import_unit/step3/', import_unit_step3, name='import_unit_step3'),
    path('import_unit/sample/', import_unit_sample, name='import_unit_sample'),
]