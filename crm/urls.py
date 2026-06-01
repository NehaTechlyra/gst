from django.urls import path, include
from . import views
from sales import views as sales_views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Leads
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/create/', views.lead_create, name='lead_create'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.lead_edit, name='lead_edit'),
    path('leads/<int:pk>/lost/', views.lead_mark_lost, name='lead_mark_lost'),
    path('leads/<int:pk>/opportunity/', views.lead_to_opportunity, name='lead_to_opportunity'),
    path('leads/<int:pk>/delete/', views.lead_delete, name='lead_delete'),
    
    # Opportunities
    path('opportunities/', views.opportunity_list, name='opportunity_list'),
    path('opportunities/<int:pk>/', views.opportunity_detail, name='opportunity_detail'),
    path('opportunities/<int:pk>/edit/', views.opportunity_edit, name='opportunity_edit'),
    path('opportunities/<int:pk>/lost/', views.opportunity_mark_lost, name='opportunity_mark_lost'),
    path('opportunities/<int:pk>/delete/', views.opportunity_delete, name='opportunity_delete'),
    
    # Quotations handled by Sales app (but CRM has its own pre-fill view)
    path('quotations/', sales_views.sales_quote_list, name='quotation_list'),
    path('quotations/create/', views.crm_quotation_create, name='quotation_create'),
    path('quotations/cancel/', views.crm_quotation_cancel, name='quotation_cancel'),
    
    # Updates
    path('updates/create/', views.update_create, name='update_create'),
    
    # Follow-ups
    path('followups/', views.followup_list, name='followup_list'),
    path('followups/create/', views.followup_create, name='followup_create'),
    path('followups/<int:pk>/complete/', views.followup_complete, name='followup_complete'),
    
    # Lost Reasons
    path('lost-reasons/create/', views.lost_reason_create, name='lost_reason_create'),
    path('lost-reasons/', views.lost_reason_list, name='lost_reason_list'),
    path('lost-reasons/<int:pk>/edit/', views.lost_reason_edit, name='lost_reason_edit'),
    path('lost-reasons/<int:pk>/delete/', views.lost_reason_delete, name='lost_reason_delete'),

    # Presales
    path('presales/create/', views.presales_create, name='presales_create'),
    path('presales/', views.presales_list, name='presales_list'),
    path('presales/<int:pk>/', views.presales_detail, name='presales_detail'),
    path('presales/<int:pk>/edit/', views.presales_edit, name='presales_edit'),
    path('presales/<int:pk>/delete/', views.presales_delete, name='presales_delete'), 
]

