from django.urls import path
# from website.views import Index
from website import views

urlpatterns = [
    path('', views.Index, name="index"),
    path('ShowStaff/', views.ShowStaff, name="showStaff"),
    path('ShowStaffData/<int:id>/', views.ViewStaffData, name="viewStaffData"),
    path('masters/', views.master_list, name='master_list'),
    path('prefix-sq/', views.prefix_sq, name='prefix_sq'),
    path('api/dashboard/layout/get/', views.get_dashboard_layout, name='dashboard_layout_get'),
    path('api/dashboard/layout/save/', views.save_dashboard_layout, name='dashboard_layout_save'),
]

