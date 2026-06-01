from django.urls import path
from . import views

urlpatterns = [
    path('personal-documents/', views.personal_document_type_list, name='personal_document_type_list'),
    path('personal-documents/add/', views.personal_document_type_create, name='personal_document_type_add'),
    path('personal-documents/<int:pk>/edit/', views.personal_document_type_edit, name='personal_document_type_edit'),
    path('personal-documents/<int:pk>/deactivate/', views.personal_document_type_deactivate, name='personal_document_type_deactivate'),
]