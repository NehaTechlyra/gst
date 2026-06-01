from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.activity_log_list, name='activity_log_list'),
    path('logs/<int:pk>/', views.activity_log_detail, name='activity_log_detail'),
    path('new_logs/<str:model>/', views.model_activity_log_list, name='model_activity_log_list'),
    path(
    'new_logs/<str:model>/<int:object_id>/',
    views.model_object_activity_log_list,
    name='model_object_activity_log_list'
),
]