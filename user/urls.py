from django.urls import path
from . import views

urlpatterns = [
    path('roles/add/', views.roles_view, name='roles_view'),
    path('roles/', views.roles_list, name='roles_list'),
    path('roles/<int:pk>/edit/', views.roles_view, name='roles_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    path('add/', views.add_user, name='add_user'),
    path('', views.user_list, name='user_list'),
    path('user/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('user/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('profile/', views.user_profile, name='user_profile'),
    # path('module/<int:pk>/edit/', views.module_edit, name='module_edit'),
    # path('module/<int:pk>/delete/', views.module_delete, name='module_delete'),

    path('validate-user-field/', views.validate_user_field, name='validate_user_field'),
]
