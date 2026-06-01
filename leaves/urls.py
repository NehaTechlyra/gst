from django.urls import path
from . import views

urlpatterns = [
    path('', views.leaves_list, name='leaves_list'),
    path('add/', views.leaves_create, name='leaves_add'),
    path('edit/<int:pk>/', views.leaves_edit, name='leaves_edit'),
    path('deactivate/<int:pk>/', views.leaves_deactivate, name='leaves_deactivate'),
]

