from django.urls import path

from . import views


urlpatterns = [
    path('', views.dashboard, name='mis_reports_dashboard'),
    path('sales/', views.sales_report, name='mis_sales_report'),
    path('sales/export-csv/', views.sales_report_export_csv, name='mis_sales_report_export_csv'),
    path('purchase/', views.purchase_report, name='mis_purchase_report'),
    path('purchase/export-csv/', views.purchase_report_export_csv, name='mis_purchase_report_export_csv'),
    path('inventory/', views.inventory_report, name='mis_inventory_report'),
    path('inventory/export-csv/', views.inventory_report_export_csv, name='mis_inventory_report_export_csv'),
    path('finance/', views.finance_report, name='mis_finance_report'),
    path('finance/export-csv/', views.finance_report_export_csv, name='mis_finance_report_export_csv'),
    path('crm/', views.crm_report, name='mis_crm_report'),
    path('crm/export-csv/', views.crm_report_export_csv, name='mis_crm_report_export_csv'),
    path('expenses/', views.expense_report, name='mis_expense_report'),
    path('expenses/export-csv/', views.expense_report_export_csv, name='mis_expense_report_export_csv'),
    path('hr/', views.hr_report, name='mis_hr_report'),
    path('hr/export-csv/', views.hr_report_export_csv, name='mis_hr_report_export_csv'),
]
