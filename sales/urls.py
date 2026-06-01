from django.urls import path
from . import views
from .views_eway_bill_api import (
    eway_bill_generate,
    eway_bill_cancel,
    eway_bill_update_vehicle,
    eway_bill_refresh,
    eway_bill_credentials,
)
from .views import (
    eway_bill_detail,
    eway_bill_list,
)
from .views_eway_bill_ajax import (
    eway_bill_test_connection,
    eway_bill_regen_app_key,
)

urlpatterns = [
    # path('', views.sales_view, name='sales_view'),
    path('quotation_add/', views.quotation_add, name='quotation_add'),
    path('customer/', views.customer_search, name='customer_search'),
    path('customer/<int:pk>/detail/', views.customer_detail_ajax, name='customer_detail_ajax'),
    path('sale_person/', views.sale_person_search, name='sale_person_search'),
    path('customer_createform/', views.create_customer_ajax, name='create_customer_ajax'),
    path('saleperson_createform/', views.create_saleperson_ajax, name='create_saleperson_ajax'),
    path('add_customer/', views.add_customer, name='add_customer'),
    path('add_salesperson/', views.add_salesperson, name='add_salesperson'),
    path('save_salesquote/', views.save_salesquote, name='save_salesquote'),
    path('get_item_sales/', views.get_item_sales, name='get_item_sales'),
    path('sales_quotes/', views.sales_quote_list, name='sales_quote_list'),
    path('sales/quotation_edit/<int:pk>/', views.quotation_edit, name='quotation_edit'),
    path('sales/quotation/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('sales/quotation/<int:pk>/print/', views.quotation_print_view, name='quotation_print'),
    path('sales/quotation/<int:pk>/pdf/', views.quotation_pdf_view, name='quotation_pdf'),
    path('sales/quotation_duplicate/<int:pk>/', views.quotation_duplicate, name='quotation_duplicate'),
    path('sales/quotation/<int:pk>/duplicate/',views.duplicate_quotation,name='duplicate_quotation'),

    path('sales/quotation/<int:quotation_id>/convert-to-order/', views.convert_quotation_to_order, name='convert_quotation_to_order'),
    
    path('sales/delete/<int:quotation_id>/', views.delete_sales_quotation, name='delete_sales_quotation'),
    path('sales/quotation/<int:quotation_id>/update-status/', views.update_quotation_status, name='update_quotation_status'),
    path('sales/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('sales/quotation/<int:pk>/send_message/', views.send_message, name='send_quotation_message'),
    # Send message endpoints for Order and Invoice (used by detail page Send -> Email)
    path('sales/order/<int:pk>/send_message/', views.send_order_message, name='send_order_message'),



    path('sales_order_list/', views.sales_Order_list, name='sales_order_list'),
    path('order_add/', views.order_add, name='order_add'),
    path('save_salesorder/', views.save_salesorder, name='save_salesorder'),
    path('sales/order/<int:pk>/duplicate/', views.duplicate_order, name='duplicate_order'),

    path('sales/order/<int:pk>/', views.order_detail, name='order_detail'),
    path('sales/order/<int:pk>/print/', views.order_print_view, name='order_print'),
    path('sales/order/<int:pk>/pdf/', views.order_pdf_view, name='order_pdf'),
    path('sales/order_edit/<int:pk>/', views.order_edit, name='order_edit'),
    path('sales/order_duplicate/<int:pk>/', views.order_duplicate, name='order_duplicate'),

    path('delete_order/<int:order_id>/', views.delete_sales_order, name='delete_sales_order'),
    path('sales/quotation/<int:quotation_id>/convert-to-inv/', views.convert_quotation_to_inv, name='convert_quotation_to_inv'),
    path('sales/order/<int:order_id>/convert-to-inv/', views.convert_order_to_inv, name='convert_order_to_inv'),
    path('sales/quotation/<int:quotation_id>/check-invoiced/', views.check_quotation_invoiced, name='check_quotation_invoiced'),

    # path('quotation_duplicate/', views.quotation_duplicate, name='quotation_duplicate'),
    path('sales_inv_list/', views.sales_inv_list, name='sales_inv_list'),
    path('inv_add/', views.inv_add, name='inv_add'),
    path('save_salesinvoice/', views.save_salesinvoice, name='save_salesinvoice'),
    path('sales/invoice/<int:pk>/duplicate/', views.duplicate_invoice, name='duplicate_invoice'),

    path('sales/invoice_edit/<int:pk>/', views.invoice_edit, name='invoice_edit'),
    path('sales/invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('sales/invoice/<int:pk>/journal/', views.invoice_journal, name='invoice_journal'),
    path('sales/invoice/<int:pk>/print/', views.invoice_print_view, name='invoice_print'),
    path('sales/invoice/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('sales/invoice/<int:invoice_id>/update-status/', views.update_invoice_status, name='update_invoice_status'),
    path('sales/invoice/<int:pk>/send_message/', views.send_invoice_message, name='send_invoice_message'),
    path('sales/invoice_duplicate/<int:pk>/', views.invoice_duplicate, name='invoice_duplicate'),

    path('delete_inv/<int:inv_id>/', views.delete_sales_inv, name='delete_sales_inv'),


    path('sales/payment_recieved/<int:pk>/', views.payment_recieved_view, name='payment_recieved_view'),
    path('invoice/<int:pk>/receive-payment/', views.receive_payment, name='receive_payment'),
    path('payment_received_list/', views.payment_received_list, name='payment_received_list'),
    # New: payment without specific bill
    path('add-payment-received/', views.add_payment_received, name='add_payment_received'),
    
    # AJAX endpoint for getting vendor's unpaid bills
    path('get-customer-unpaid-invoices/', views.get_customer_unpaid_invoices, name='get_customer_unpaid_invoices'),

    path('payment_received/edit/<int:payment_id>/', views.edit_payment_received, name='edit_payment_received'),

    path('payment_received/payment/<int:payment_id>/', views.payment_received_detail, name='payment_received_detail'),
    path('payment_received/delete/<int:payment_id>/', views.delete_payment_received, name='delete_payment_received'),
    path('payment_received/<int:payment_id>/print/', views.payment_received_print, name='payment_received_print'),
    path('payment_received/<int:payment_id>/receipt/', views.download_payment_receipt, name='download_payment_receipt'),


    # Sales Delivery Note URLs
    path('delivery-notes/', views.SalesDeliveryNoteListView.as_view(), name='sales_delivery_note_list'),
    path('delivery-notes/create/', views.SalesDeliveryNoteCreateView.as_view(), name='sales_delivery_note_create'),
    path('delivery-notes/<int:pk>/', views.SalesDeliveryNoteDetailView.as_view(), name='sales_delivery_note_detail'),
    path('delivery-notes/<int:pk>/edit/', views.SalesDeliveryNoteUpdateView.as_view(), name='sales_delivery_note_edit'),
    path('delivery-notes/<int:pk>/mark-delivered/', views.sales_delivery_note_mark_delivered, name='sales_delivery_note_mark_delivered'),
    path('delivery-notes/<int:pk>/print/', views.sales_delivery_note_print, name='sales_delivery_note_print'),
    path('delivery-notes/<int:pk>/cancel/', views.sales_delivery_note_cancel, name='sales_delivery_note_cancel'),
    
    # API URLs for AJAX
    path('api/invoices/<int:invoice_id>/items/', views.get_invoice_items, name='api_invoice_items'),
    path('api/invoices/<int:invoice_id>/', views.get_invoice_details, name='api_invoice_details'),

    path('add_unit/', views.add_unit_from_sales, name='add_unit'),


    # Sales return Note URLs
    path('sales/invoice/<int:pk>/return/', views.sales_return_view, name='sales_invoice_return'),
    path('sales/returns/', views.sales_return_list, name='sales_return_list'),
    path('sales/returns/create/', views.sales_return_create, name='sales_return_create'),
    path('sales/returns/invoice/<int:invoice_id>/items/', views.sales_return_invoice_items, name='sales_return_invoice_items'),
    path('sales/return/<int:pk>/', views.sales_return_detail, name='sales_return_detail'),
     path('sales/return/<int:pk>/edit/', views.SalesReturnUpdateView.as_view(), name='sales_return_edit'),
    path('sales/return/<int:pk>/print/', views.sales_return_print, name='sales_return_print'),
    path('sales/return/<int:pk>/cancel/', views.sales_return_cancel, name='sales_return_cancel'),
    path('sales/return/<int:pk>/mark-received/', views.sales_return_mark_received, name='sales_return_mark_received'),


    path('performa_inv_list/', views.performa_inv_list, name='performa_inv_list'),
    path('performa_add/', views.performa_inv_add, name='performa_inv_add'),
    path('performa_edit/<int:pk>/', views.performa_invoice_edit, name='performa_invoice_edit'),
    path('save_performa_invoice/', views.save_performa_invoice, name='save_performa_invoice'),
    path('sales/performa-invoice/<int:pk>/', views.performa_invoice_detail, name='performa_invoice_detail'),
    path('sales/performa-invoice/<int:pk>/print/', views.performa_invoice_print_view, name='performa_invoice_print'),
    path('sales/performa-invoice/<int:pk>/pdf/', views.performa_invoice_pdf_view, name='performa_invoice_pdf'),
    path('sales/performa-invoice/<int:invoice_id>/update-status/', views.update_performa_status, name='update_performa_status'),
    path('sales/performa-invoice/<int:pk>/send_message/', views.send_performa_invoice_message, name='send_performa_invoice_message'),
    path('sales/performa-invoice/<int:performa_id>/convert-to-order/', views.convert_performa_to_order, name='convert_performa_to_order'),
    path('delete_performa_inv/<int:inv_id>/', views.delete_performa_inv, name='delete_performa_inv'),

     # E-Way Bill URLs
    path('eway-bills/', eway_bill_list, name='eway_bill_list'),
    path('eway-bills/credentials/', eway_bill_credentials, name='eway_bill_credentials'),
    path('eway-bills/<int:pk>/', eway_bill_detail, name='eway_bill_detail'),
    path('eway-bills/<int:invoice_id>/generate/', eway_bill_generate, name='eway_bill_generate'),
    path('eway-bills/<int:pk>/cancel/', eway_bill_cancel, name='eway_bill_cancel'),
    path('eway-bills/<int:pk>/update-vehicle/', eway_bill_update_vehicle, name='eway_bill_update_vehicle'),
    path('eway-bills/<int:pk>/refresh/', eway_bill_refresh, name='eway_bill_refresh'),
    
    # E-Way Bill AJAX endpoints
    path('eway-bills/test-connection/', eway_bill_test_connection, name='eway_bill_test_connection'),
    path('eway-bills/regen-app-key/', eway_bill_regen_app_key, name='eway_bill_regen_app_key'),
    # Dashboard
    path('dashboard/', views.sales_dashboard, name='sales_dashboard'),
]
