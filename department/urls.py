from django.urls import path
from . import views

urlpatterns = [
    path('', views.department_list, name='department_list'),
    path('add/', views.department_create, name='department_add'),
    path('edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('deactivate/<int:pk>/', views.department_deactivate, name='department_deactivate'),
]
