from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.email_config_list, name='email_config_list'),
    path('add/', views.email_config_create, name='email_config_create'),  
    path('edit/<int:pk>/', views.email_config_edit, name='email_config_edit'),
    path('deactivate/<int:pk>/', views.email_config_deactivate, name='email_config_deactivate'),
    path('set_default/<int:id>/', views.email_set_default, name='email_set_default'),
]
