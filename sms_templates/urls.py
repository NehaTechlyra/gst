from django.urls import path
from . import views

urlpatterns = [
    path("", views.sms_template_list, name="sms_template_list"),
    path("create/", views.sms_template_create, name="sms_template_create"),
    path("edit/<int:pk>/", views.sms_template_edit, name="sms_template_edit"),
    path("delete/<int:pk>/", views.sms_template_delete, name="sms_template_delete"),
    # CHANGE THIS LINE - use template_name and style instead of pk
    path("set-default/<str:template_name>/<str:style>/", views.sms_template_set_default, name="sms_template_set_default"),
]