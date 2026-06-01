from django.urls import path
from . import views

urlpatterns = [
    path('master-dashboard/', views.masters_dashboard, name='masters_dashboard'),
    
]
