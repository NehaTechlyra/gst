from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('currency/add/', views.currency_create, name='currency_add'),
    path('<int:pk>/', views.expense_detail, name='expense_detail'),
    path('<int:pk>/journal/', views.expense_journal, name='expense_journal'),
    path('<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
]
