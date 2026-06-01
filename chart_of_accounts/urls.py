from django.urls import path
from . import views


urlpatterns = [
    # Define app URLs here later
    # path('', account, name='account'),
    path('', views.account_list, name='accounts-list'),  # Lists accounts in accounts_list.html
    path('create/', views.create_account, name='create_account'),
    path('create_acc/', views.create_account_tree, name='create_account_tree'),
    path('ajax/get-parents/', views.get_parents_for_type, name='get_parents_for_type'),
    path('ajax/get-account-types/', views.get_account_types, name='get_account_types'),
    path('ajax/create-account/', views.create_account_ajax, name='ajax-create-account'),
    path('edit/<int:pk>/', views.edit_account, name='edit_account'),
    path('delete/<int:pk>/', views.delete_account, name='delete_account'),
    path('detail/<int:pk>/', views.account_detail, name='account_detail'),
    path('detail/<int:pk>/pdf/', views.account_ledger_download_pdf, name='account_ledger_download_pdf'),
    path('party/<str:party_type>/<int:pk>/', views.party_transactions, name='party_transactions'),
    path('party/<str:party_type>/<int:pk>/pdf/', views.party_transactions_pdf, name='party_transactions_pdf'),
    # urls.py
    path('generate_code/', views.generate_code_ajax, name='generate-code-ajax'),
    path('chart_of_accounts_tree/', views.chart_of_accounts_tree, name='chart_of_accounts_tree'),
    path('balance-sheet/', views.balance_sheet_report, name='balance_sheet'),
    path('balance-sheet/pdf/', views.balance_sheet_pdf, name='balance_sheet_pdf'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss'),
    path('profit-loss/pdf/', views.profit_loss_pdf, name='profit_loss_pdf'),
    path('trial-balance/', views.trial_balance_report, name='trial_balance'),
    path('trial-balance/pdf/', views.trial_balance_pdf, name='trial_balance_pdf'),
    path('cash-flow/', views.cash_flow_report, name='cash_flow'),
    path('cash-flow/pdf/', views.cash_flow_pdf, name='cash_flow_pdf'),
    path('debug/', views.debug_accounts, name='debug_accounts'),
    path('inventory-valuation-summary/', views.inventory_valuation_summary, name='inventory_valuation_summary'),
]