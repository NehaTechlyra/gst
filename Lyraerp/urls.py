"""Lyraerp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from Lyraerp.views import Signup, LoginView, LogoutView, CompanyPasswordResetView
from . import views
from company.views import activate_license, license_restricted_view, trial_expired_page
from company.debug_license_status import debug_license_status

def redirect_to_admin(request, company_code, admin_path=''):
    url = f'/admin/{admin_path}'
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    return redirect(url)

urlpatterns = [
    # public endpoints – do not include company_code prefix
    path('admin/', admin.site.urls),
    path('login/', LoginView, name='login'),
    path('login/<str:company_code>/', views.LoginView, name='login_with_code'),
    path('logout/', LogoutView, name='logout'),
    path('signup/', Signup, name='signup'),
    # also accept capitalized variant (some links use /Signup/)
    path('Signup/', Signup),
    # Password reset (plain URLs)
    path('password-reset/', CompanyPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # status endpoint; we accept both the bare path and a company-prefixed
    # version so AJAX polls work no matter which namespace they're sent from.
    path('_migration_status/', include('Lyraerp.migration_status_urls')),
    path('<str:company_code>/_migration_status/', include('Lyraerp.migration_status_urls')),
    
    # Debug endpoints for license status
    path('debug-license-status/', debug_license_status, name='debug_license_status'),

    # Tenant-aware login (company-prefixed) - used when session expires on company pages
    path('<str:company_code>/login/', views.LoginView, name='login_company_prefixed'),

    # Tenant-aware password reset (company-prefixed)
    path('<str:company_code>/password-reset/', CompanyPasswordResetView.as_view(), name='password_reset_with_code'),
    path('<str:company_code>/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done_with_code'),
    path('<str:company_code>/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm_with_code'),
    path('<str:company_code>/password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete_with_code'),

    path('<str:company_code>/activate-license/', activate_license, name='activate_license'),
    path('<str:company_code>/license/restricted/', license_restricted_view, name='license_restricted'),
    path('<str:company_code>/trial-expired/', trial_expired_page, name='trial_expired_page'),

    # License activation (tenant-aware)
    path('<str:company_code>/activate-license/', activate_license, name='activate_license'),

    # tenant-aware URLs start here
    path('<str:company_code>/admin/', redirect_to_admin),
    path('<str:company_code>/admin/<path:admin_path>', redirect_to_admin),
    path('<str:company_code>/', include('website.urls')),
    path('<str:company_code>/Project/', include('Project.urls')),
    path('<str:company_code>/Employee/', include('Employee.urls')),
    path('<str:company_code>/purchase/', include('Purchase.urls')),  # Link to purchase module
    path('<str:company_code>/tax/', include('Tax.urls')),
    path('<str:company_code>/user/', include('user.urls')),
    path('<str:company_code>/customer/', include('customer.urls')),
    path('<str:company_code>/brand/', include('brand.urls')),
    path('<str:company_code>/Items/', include('Items.urls')),
    path('<str:company_code>/category/', include('category.urls')),
    path('<str:company_code>/type/', include('type.urls')),
    path('<str:company_code>/chart_of_accounts/', include('chart_of_accounts.urls')),
    path('<str:company_code>/UserReq/', include('UserReq.urls')),
    path('<str:company_code>/unit/', include('unit.urls')),
    path('<str:company_code>/warehouse/', include('warehouse.urls')),
    path('<str:company_code>/stock/', include('stock.urls')),
    path('<str:company_code>/PayTerms/', include('PayTerms.urls')),
    path('<str:company_code>/sales/', include('sales.urls')),
    path('<str:company_code>/HR/', include('HR.urls')),
    path('<str:company_code>/masters/', include('masters.urls')),
    path('<str:company_code>/department/', include('department.urls')),
    path('<str:company_code>/designation/', include('designation.urls')),
    path('<str:company_code>/company/', include('company.urls')),
    path('<str:company_code>/currencies/', include('currencies.urls')),
    path('<str:company_code>/leaves/', include('leaves.urls')),
    path('<str:company_code>/bank/', include('bank.urls')),
    path('<str:company_code>/allowances/', include('allowances.urls')),
    path('<str:company_code>/personaldocuments/',include('personaldocuments.urls')),
    path('<str:company_code>/email_config/', include('email_config.urls')),
    path('<str:company_code>/sms_config/', include('sms_config.urls')),
    path('<str:company_code>/email_templates/', include('email_templates.urls')),
    path('<str:company_code>/sms_templates/', include('sms_templates.urls')),
    path('<str:company_code>/system_settings/', include('system_settings.urls')),
    path('<str:company_code>/expenses/', include('expenses.urls')),
    path('<str:company_code>/journal/', include('journal.urls')),
    path('<str:company_code>/crm/', include('crm.urls')),
    path('<str:company_code>/activity/', include('activity_log.urls')),
    path('<str:company_code>/pricelists/', include('pricelists.urls')),


    # ===== AJAX ENDPOINTS =====
    path('check-email/', views.check_email_exists, name='check_email_exists'),
    path('check-username/', views.check_username_exists, name='check_username_exists'),
    path('api/migration-status/', views.migration_status, name='migration_status'),



] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
