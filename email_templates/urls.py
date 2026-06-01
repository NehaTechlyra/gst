from django.urls import path
from . import views

urlpatterns = [
    path("", views.email_template_list, name="email_template_list"),
    path("create/", views.email_template_create, name="email_template_create"),
    path("edit/<int:pk>/", views.email_template_edit, name="email_template_edit"),
    path("delete/<int:pk>/", views.email_template_delete, name="email_template_delete"),
    path("set-default/<str:template_name>/<str:style>/", views.set_default_email_template, name="set_default_email_template"),
    path("upload/", views.summernote_upload, name="summernote_upload"),
]