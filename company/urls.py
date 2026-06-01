from django.urls import path
from .import views
from .import registration_views

urlpatterns = [
    # Company
    path("company/", views.company_list, name="company_list"),
    path("company/create/", views.company_create, name="company_create"),
    path("company/infer-currency/", views.infer_currency_for_country, name="company_infer_currency"),
    path("company/<int:pk>/update/", views.company_update, name="company_update"),
    path("company/<int:pk>/delete/", views.company_delete, name="company_delete"),

    # BANK ACCOUNTS
    path("company/<int:company_id>/bank-accounts/", views.company_bank_list, name="company_bank_list"),
    path("bank-accounts/", views.company_bank_list_no_company, name="company_bank_list_no_id"),
    path("company/<int:company_id>/bank-accounts/create/", views.company_bank_create, name="company_bank_create"),
    path("bank-accounts/<int:pk>/update/", views.company_bank_update, name="company_bank_update"),
    path("bank-accounts/<int:pk>/delete/", views.company_bank_delete, name="company_bank_delete"),
    
    # AJAX Bank endpoints
    path("company/bank-accounts/ajax-list/", views.bank_accounts_ajax_list, name="bank_accounts_ajax_list"),
    path("company/bank-accounts/ajax-create/", views.bank_account_ajax_create, name="bank_account_ajax_create"),
    path("company/bank-accounts/ajax-delete/<int:pk>/", views.bank_account_ajax_delete, name="bank_account_ajax_delete"),
    path('bank-account/get/<int:pk>/', views.bank_account_ajax_get, name='bank_account_ajax_get'),
    path('bank-account/update/<int:pk>/', views.bank_account_ajax_update, name='bank_account_ajax_update'),
    path('company/bank/add/', views.add_bank, name='add_bank'),

    # LOCATION TYPES
    path("location-types/", views.location_type_list, name="location_type_list"),
    path("location-types/create/", views.location_type_create, name="location_type_create"),
    path("location-types/<int:pk>/update/", views.location_type_update, name="location_type_update"),
    path("location-types/<int:pk>/delete/", views.location_type_delete, name="location_type_delete"),

    # LOCATIONS
    path("company/<int:company_id>/locations/", views.location_list, name="location_list"),
    path("locations/", views.location_list_no_company, name="location_list_no_id"),
    path("company/<int:company_id>/locations/create/", views.location_create, name="location_create"),
    path("locations/<int:pk>/update/", views.location_update, name="location_update"),
    path("locations/<int:pk>/delete/", views.location_delete, name="location_delete"),
    
    # AJAX Location endpoints
    path("company/locations/ajax-list/", views.locations_ajax_list, name="locations_ajax_list"),
    path("company/locations/ajax-create/", views.location_ajax_create, name="location_ajax_create"),
    path("company/locations/ajax-delete/<int:pk>/", views.location_ajax_delete, name="location_ajax_delete"),
    path('location/get/<int:pk>/', views.location_ajax_get, name='location_ajax_get'),
    path('location/update/<int:pk>/', views.location_ajax_update, name='location_ajax_update'),

    path("company/setup-complete/<int:company_id>/", views.company_setup_complete, name="company_setup_complete"),

    # License Key URLs 
    path('license/configuration/<int:company_id>/', views.get_license_configuration, name='get_license_configuration'),
    path('license/save/', views.save_license_configuration, name='save_license_configuration'),
    path('license/validate/', views.validate_license_key, name='validate_license_key'),
    path('license/check/<int:company_id>/<str:module_code>/', views.check_module_access, name='check_module_access'),
    
    # License Error Pages
    path('license/expired/', views.license_expired, name='license_expired'),
    path('license/required/', views.license_required, name='license_required'),
    path('license/module-denied/', views.module_not_allowed, name='module_not_allowed'),


    # ========================================
    # COMPANY REGISTRATION (First-Time Setup)
    # ========================================
    path("setup/", registration_views.company_registration, name="company_registration"),
    path("setup/company-info/", registration_views.register_company_info, name="register_company_info"),
    path("setup/load-countries/", registration_views.load_countries, name="load_countries"),
    path("setup/load-states/", registration_views.load_states, name="load_states"),
    path("setup/load-cities/", registration_views.load_cities, name="load_cities"),
    path('setup/fiscal-year/', registration_views.register_fiscal_year, name='register_fiscal_year'),
    path("setup/license-activation/", registration_views.register_license_activation, name="register_license_activation"),
    path("setup/complete/", registration_views.complete_registration, name="complete_registration"),
    path("setup/status/", registration_views.check_registration_status, name="check_registration_status"),


    path('license/restricted/', views.site_blocked_view, name='license_restricted'),
    

]