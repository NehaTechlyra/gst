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
from Lyraerp.views import SignUpView, LoginView, LogoutView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('Project/', include('Project.urls')),
    path('Employee/', include('Employee.urls')),
    path('purchase/', include('Purchase.urls')),  # Link to purchase module
    path('tax/', include('Tax.urls')),
    path('user/', include('user.urls')),
    path('customer/', include('customer.urls')),
    path('brand/', include('brand.urls')),
    path('Items/', include('Items.urls')),
    path('chart_of_accounts/', include('chart_of_accounts.urls')),
    path('UserReq/', include('UserReq.urls')),
    path('unit/', include('unit.urls')),
    path('warehouse/', include('warehouse.urls')),
    path('stock/', include('stock.urls')),
    path('PayTerms/', include('PayTerms.urls')),
    path('sales/', include('sales.urls')),
    path('HR/', include('HR.urls')),
    path('department/', include('department.urls')),
    path('designation/', include('designation.urls')),
    path('leaves/', include('leaves.urls')),
    path('bank/', include('bank.urls')),
    path('allowances/', include('allowances.urls')),
    path('journal/', include('journal.urls')),
    path('expenses/', include('expenses.urls')),
    
    #SignUp, Login
    
    path('Signup/', SignUpView.as_view(), name="signup"),
    path('login/', LoginView, name='login'),
    path('logout/', LogoutView, name='logout'),



] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
