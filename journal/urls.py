from django.urls import path
from . import views

urlpatterns = [
    path('journals/', views.journal_list, name='journal_list'),
    path('journals/create/', views.journal_create, name='journal_create'),
    path('journals/<int:pk>/', views.journal_detail, name='journal_detail'),
    path('journals/<int:pk>/edit/', views.journal_edit, name='journal_edit'),
    path('journals/<int:pk>/delete/', views.journal_delete, name='journal_delete'),
]