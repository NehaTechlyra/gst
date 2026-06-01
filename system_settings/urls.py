from django.urls import path
from . import views

urlpatterns = [
    
    path('settings/', views.settings_page, name='settings_page'),
    
    #updt by neha on 4-3-26
    path('settings/prefix/update/', views.prefix_update, name='prefix_update'),
    path('settings/backup/now/', views.backup_now, name='backup_now'),
    path('settings/backup/schedule/update/', views.backup_schedule_update, name='backup_schedule_update'),
    path('settings/backup/download/', views.backup_download, name='backup_download'),
    path('settings/backup/download/<str:filename>/', views.backup_download, name='backup_download_legacy'),

    # ────────────────────────────────────────────────────────────────────
    # PERIOD LOCKING - Fiscal Year & Period Management
    # ────────────────────────────────────────────────────────────────────
    path('periods/', views.period_management, name='period_management'),
    path('periods/create/', views.create_fiscal_year, name='create_fiscal_year'),
    path('periods/<int:pk>/edit/', views.edit_fiscal_year, name='edit_fiscal_year'),
    path('periods/<int:pk>/lock/', views.lock_fiscal_year, name='lock_fiscal_year'),
    path('periods/<int:pk>/unlock/', views.unlock_fiscal_year, name='unlock_fiscal_year'),
    path('periods/check/<str:date_str>/', views.check_period_lock, name='check_period_lock'),
    path('periods/<int:pk>/exemption/', views.grant_exemption, name='grant_exemption'),
    path('periods/history/<int:pk>/delete/', views.delete_period_lock, name='delete_period_lock'),
    path('periods/exemption/<int:pk>/delete/', views.delete_exemption, name='delete_exemption'),
    path('periods/reports/', views.period_lock_reports, name='period_lock_reports'),

     # ────────────────────────────────────────────────────────────────────
    # FISCAL YEAR CLOSING - Year-end closing process
    # ────────────────────────────────────────────────────────────────────
    path('fiscal-closing/', views.fiscal_year_closing_dashboard, name='fiscal_year_closing_dashboard'),
    path('fiscal-closing/<int:pk>/prepare/', views.prepare_fiscal_year_closing, name='prepare_fiscal_year_closing'),
    path('fiscal-closing/<int:pk>/execute/', views.execute_fiscal_year_closing, name='execute_fiscal_year_closing'),
    path('fiscal-closing/<int:pk>/details/', views.fiscal_year_closing_details, name='fiscal_year_closing_details'),
    path('fiscal-closing/<int:pk>/delete/', views.delete_fiscal_year_closing, name='delete_fiscal_year_closing'),
]

