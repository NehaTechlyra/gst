from django.urls import path
from . import views

urlpatterns = [
    path('', views.sms_config_list, name='sms_config_list'),
    path('add/', views.sms_config_create, name='sms_config_add'),
    path('edit/<int:pk>/', views.sms_config_edit, name='sms_config_edit'),
    path('deactivate/<int:pk>/', views.sms_config_deactivate, name='sms_config_deactivate'),
    path('sms/default/<int:id>/', views.sms_set_default, name="sms_set_default"),

]
