from django.urls import path

from . import views
from . import vendor_import_views

urlpatterns = [
    #vendor
    path('vendors/', views.vendor_list, name='vendor_list'),
    path('vendors/add/', views.vendor_create, name='vendor_create'),


    # path('', views.create_purchase_order, name='create_purchase_order'), 
    # path('purchase/', views.pur, name='pur'),
    path('pur_trial/', views.pur, name='pur'),
    

    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('vendor/add/modal/', views.vendor_add_modal, name='vendor_add_modal'),
    path('vendor-choices-partial/', views.vendor_choices_partial, name='vendor_choices_partial'),
    # path('save_purchase_order/', views.save_purchase_order, name='save_purchase_order'),
    path('get_item/', views.get_item, name='get_item'),
    path('get_tax/', views.get_tax, name='get_tax'),

    # ... other purchase module URLs
    # path('add-items/<int:po_id>/', views.add_purchase_order_items, name='add_purchase_order_items'),
    path('vendor/<int:pk>/edit/', views.vendor_edit, name='vendor_edit'),
    path('vendor/<int:pk>/delete/', views.vendor_delete, name='vendor_delete'),
    path('product/add/modal/', views.product_add_modal, name='product_add_modal'),
    path("product-choices/", views.product_choices_partial, name="product_choices_partial"),
    #added by neha on 17-12-25
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase_order_add/', views.purchase_order_add, name='purchase_order_add'),
    path('vendor/', views.vendor_search, name='vendor_search'),
    path('vendor_createform/', views.create_vendor_ajax, name='create_vendor_ajax'),
    path('vendor/<int:pk>/detail/', views.vendor_detail_ajax, name='vendor_detail_ajax'),
    path('add_vendor/', views.add_vendor, name='add_vendor'),

    path('get_item_purchase/', views.get_item_purchase, name='get_item_purchase'),
    path('save_purchaseorder/', views.save_purchaseorder, name='save_purchaseorder'),
    path('purchase/order/<int:pk>/', views.purchaseorder_detail, name='purchaseorder_detail'),

    path('purchase/purchase_order_edit/<int:pk>/', views.purchase_order_edit, name='purchase_order_edit'),
    path('purchase/order_duplicate/<int:pk>/', views.purchase_order_duplicate, name='purchase_order_duplicate'),
    path('purchase/delete/<int:order_id>/', views.delete_purchase_order, name='delete_purchase_order'),
    path('purchase/order/<int:order_id>/convert-to-order/', views.convert_purchase_order_to_bill, name='convert_purchase_order_to_bill'),
    path('purchase/order/<int:order_id>/update-status/', views.update_purchase_order_status, name='update_purchase_order_status'),

    path('purchase-bills/', views.bill_list, name='bill_list'),
    path('bill_add/', views.bill_add, name='bill_add'),
    path('save_bill/', views.save_bill, name='save_bill'),
    path('purchase/bill/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('purchase/bill_edit/<int:pk>/', views.bill_edit, name='bill_edit'),
    path('purchase/bill/delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),

    path('purchase/bill_duplicate/<int:pk>/', views.bill_duplicate, name='bill_duplicate'),
    path('purchase/record_payment/<int:pk>/', views.record_payment_view, name='record_payment_view'),
    path('bill/<int:pk>/record-payment/', views.record_payment, name='record_payment'),
    path('payment_list/', views.payment_list, name='payment_list'),
    # New: payment without specific bill
    path('add-payment/', views.add_payment, name='add_payment'),
    
    # AJAX endpoint for getting vendor's unpaid bills
    path('get-vendor-unpaid-bills/', views.get_vendor_unpaid_bills, name='get_vendor_unpaid_bills'),
    path('get-vendor-info/', views.get_vendor_info, name='get_vendor_info'),
    path('payments/edit/<int:payment_id>/', views.edit_payment, name='edit_payment'),
    # added by neha on 17-2-26 for payment deletion
    path('payment/delete/<int:payment_id>/',views.delete_payment_made, name='delete_payment_made'),

    path('payment/payment/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('payment/<int:payment_id>/receipt/', views.download_bill_payment_receipt, name='download_bill_payment_receipt'),
    path('payment/<int:payment_id>/print/', views.bill_payment_print, name='bill_payment_print'),
    path('purchase/bill/<int:bill_id>/update-status/', views.update_purchase_bill_status, name='update_purchase_bill_status'),
    path('purchase/order/<int:pk>/pdf/', views.purchaseorder_pdf_view, name='purchaseorder_pdf'),
    path('purchase/order/<int:pk>/send_message/', views.send_purchaseorder_message, name='send_purchaseorder_message'),
    path('purchase/order/<int:pk>/print/', views.purchaseorder_print_view, name='purchaseorder_print'),
    
    path('purchase/bill/<int:pk>/pdf/', views.bill_pdf_view, name='bill_pdf'),
    path('purchase/bill/<int:pk>/print/', views.bill_print_view, name='bill_print'),
    path('purchase/bill/<int:pk>/send_message/', views.send_bill_message, name='send_bill_message'),

    # updated by sree on 27-01-26 for delivery details page
    # Delivery Note URLs
    path('delivery-notes/', views.DeliveryNoteListView.as_view(), name='delivery_note_list'),
    path('delivery-notes/create/', views.DeliveryNoteCreateView.as_view(), name='delivery_note_create'),
    path('delivery-notes/<int:pk>/', views.DeliveryNoteDetailView.as_view(), name='delivery_note_detail'),
    path('delivery-notes/<int:pk>/edit/', views.DeliveryNoteUpdateView.as_view(), name='delivery_note_edit'),
    path('delivery-notes/<int:pk>/mark-delivered/', views.delivery_note_mark_delivered, name='delivery_note_mark_delivered'),
    path('delivery-notes/<int:pk>/cancel/', views.delivery_note_cancel, name='delivery_note_cancel'),
    
    # API URLs for AJAX
    path('api/bills/<int:bill_id>/items/', views.get_bill_items, name='api_bill_items'),
    path('api/bills/<int:bill_id>/', views.get_bill_details, name='api_bill_details'),

    path('generate-vendor-code/', views.generate_vendor_code, name='generate_vendor_code'),
    path('vendor/<int:vendor_id>/preferred-items/', views.get_vendor_preferred_items, name='vendor_preferred_items'),
    path('purchase/delivery-notes/<int:pk>/print/', views.delivery_note_print, name='delivery_note_print'),

    # Purchase Return URLs
    path('purchase/bill/<int:pk>/return/', views.purchase_return_view, name='purchase_bill_return'),
    path('purchase/returns/create/', views.purchase_return_create, name='purchase_return_create'),
    path('purchase/returns/bill/<int:bill_id>/items/', views.purchase_return_bill_items, name='purchase_return_bill_items'),
    path('purchase/return/<int:pk>/', views.purchase_return_detail, name='purchase_return_detail'),
    path('purchase/return/<int:pk>/edit/', views.PurchaseReturnUpdateView.as_view(), name='purchase_return_edit'),
    path('purchase/return/<int:pk>/print/', views.purchase_return_print, name='purchase_return_print'),
    path('purchase/return/<int:pk>/cancel/', views.purchase_return_cancel, name='purchase_return_cancel'),
    path('purchase/return/<int:pk>/mark-received/', views.purchase_return_mark_received, name='purchase_return_mark_received'),
    # Purchase Returns list (no permission required to view link)
    path('purchase/returns/', views.purchase_return_list, name='purchase_return_list'),
    
    #import & export URLs for vendor
    path('import/step1/', vendor_import_views.import_vendors_step1, name='import_vendors_step1'),
    path('import/step2/', vendor_import_views.import_vendors_step2, name='import_vendors_step2'),
    path('import/step3/', vendor_import_views.import_vendors_step3, name='import_vendors_step3'),
    path('import/sample/', vendor_import_views.import_vendors_sample, name='import_vendors_sample'),
    path('export/csv/', vendor_import_views.export_vendors_csv, name='export_vendors_csv'),

    # Dashboard
    path('dashboard/', views.purchase_dashboard, name='purchase_dashboard'),
]
