from django.urls import path
from . import views

urlpatterns = [
    path('', views.bank_list, name='bank_list'),
    path('add/', views.bank_create, name='bank_add'),
    path('edit/<int:pk>/', views.bank_edit, name='bank_edit'),
    path('deactivate/<int:pk>/', views.bank_deactivate, name='bank_deactivate'),
    
    # Banking Dashboard
    path('banking/', views.banking_dashboard, name='banking_dashboard'),
    
    # Bank Reconciliation URLs (Zoho Books style with CSV import)
    path('reconciliation/<int:account_id>/list/', views.reconciliation_list, name='reconciliation_list'),
    path('reconciliation/', views.reconciliation_overview, name='reconciliation_overview'),
    path('reconciliation/<int:account_id>/start/', views.reconciliation_start_form, name='reconciliation_start_form'),
    path('reconciliation/<int:reconciliation_id>/csv-upload/', views.bank_statement_csv_upload, name='bank_statement_csv_upload'),
    path('reconciliation/<int:reconciliation_id>/working/', views.reconciliation_working_screen, name='reconciliation_working_screen'),
    path('reconciliation/<int:reconciliation_id>/pdf/', views.reconciliation_pdf_view, name='reconciliation_pdf'),
    # Bank rule management
    path('rules/<int:account_id>/', views.bank_rules_list, name='bank_rules_list'),
    path('rules/<int:account_id>/add/', views.bank_rule_create, name='bank_rule_create'),
    path('rules/<int:account_id>/<int:rule_id>/edit/', views.bank_rule_edit, name='bank_rule_edit'),
    path('rules/<int:account_id>/<int:rule_id>/delete/', views.bank_rule_delete, name='bank_rule_delete'),
    
    # Reconciliation Actions
    path('reconciliation/<int:reconciliation_id>/toggle-transaction/', views.reconciliation_toggle_transaction, name='reconciliation_toggle_transaction'),
    path('reconciliation/<int:reconciliation_id>/complete/', views.reconciliation_complete, name='reconciliation_complete'),
    path('reconciliation/<int:reconciliation_id>/undo/', views.reconciliation_undo, name='reconciliation_undo'),
    path('reconciliation/<int:reconciliation_id>/delete/', views.reconciliation_delete, name='reconciliation_delete'),
    path('reconciliation/<int:reconciliation_id>/create-manual-entry/', views.create_manual_entry_from_statement, name='create_manual_entry_from_statement'),
]


