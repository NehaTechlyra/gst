from django.urls import path

from . import views


urlpatterns = [
    path('', views.dashboard, name='mis_reports_dashboard'),
    path('sales/', views.sales_report, name='mis_sales_report'),
    path('sales/customer/', views.sales_by_customer_report, name='mis_sales_by_customer_report'),
    path('sales/customer/export-csv/', views.sales_by_customer_report_export_csv, name='mis_sales_by_customer_report_export_csv'),
    path('sales/salesperson/', views.sales_by_salesperson_report, name='mis_sales_by_salesperson_report'),
    path('sales/salesperson/export-csv/', views.sales_by_salesperson_report_export_csv, name='mis_sales_by_salesperson_report_export_csv'),
    path('sales/item/', views.sales_by_item_report, name='mis_sales_by_item_report'),
    path('sales/item/export-csv/', views.sales_by_item_report_export_csv, name='mis_sales_by_item_report_export_csv'),
    path('sales/export-csv/', views.sales_report_export_csv, name='mis_sales_report_export_csv'),
    path('purchase/', views.purchase_report, name='mis_purchase_report'),
    path('purchase/export-csv/', views.purchase_report_export_csv, name='mis_purchase_report_export_csv'),
    path('purchase/vendor/', views.purchase_by_vendor_report, name='mis_purchase_by_vendor_report'),
    path('purchase/vendor/export-csv/', views.purchase_by_vendor_report_export_csv, name='mis_purchase_by_vendor_report_export_csv'),
    path('purchase/item/', views.purchase_by_item_report, name='mis_purchase_by_item_report'),
    path('purchase/item/export-csv/', views.purchase_by_item_report_export_csv, name='mis_purchase_by_item_report_export_csv'),
    path('inventory/', views.inventory_report, name='mis_inventory_report'),
    path('inventory/summary/', views.inventory_report_summary, name='mis_inventory_report_summary'),
    path('inventory/warehouses/', views.inventory_warehouses_report, name='mis_inventory_warehouses_report'),
    path('inventory/warehouses/export-csv/', views.inventory_warehouses_report_export_csv, name='mis_inventory_warehouses_report_export_csv'),
    path('inventory/export-csv/', views.inventory_report_export_csv, name='mis_inventory_report_export_csv'),
    path('finance/', views.finance_report, name='mis_finance_report'),
    path('finance/export-csv/', views.finance_report_export_csv, name='mis_finance_report_export_csv'),
    path('finance/accounts/', views.account_ledgers, name='mis_account_ledgers'),
    path('finance/accounts/export-csv/', views.account_ledgers_export_csv, name='mis_account_ledgers_export_csv'),
    path('finance/account/<int:pk>/', views.account_detail, name='mis_account_detail'),
    path('crm/', views.crm_report, name='mis_crm_report'),
    path('crm/export-csv/', views.crm_report_export_csv, name='mis_crm_report_export_csv'),
    path('expenses/', views.expense_report, name='mis_expense_report'),
    path('expenses/export-csv/', views.expense_report_export_csv, name='mis_expense_report_export_csv'),
    path('hr/', views.hr_report, name='mis_hr_report'),
    path('hr/export-csv/', views.hr_report_export_csv, name='mis_hr_report_export_csv'),
]
