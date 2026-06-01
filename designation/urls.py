from django.urls import path
from . import views

urlpatterns = [
    path('', views.designation_list, name='designation_list'),
    path('add/', views.designation_create, name='designation_add'),
    path('edit/<int:pk>/', views.designation_edit, name='designation_edit'),
    path('deactivate/<int:pk>/', views.designation_deactivate, name='designation_deactivate'),
]

