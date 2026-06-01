from django.urls import path
from . import views

urlpatterns = [
    path('', views.allowances_list, name='allowances_list'),
    path('add/', views.allowances_create, name='allowances_add'),
    path('edit/<int:pk>/', views.allowances_edit, name='allowances_edit'),
    path('deactivate/<int:pk>/', views.allowances_deactivate, name='allowances_deactivate'),
]

