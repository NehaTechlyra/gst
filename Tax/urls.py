from django.urls import path
from . import views
from .import_tax_views import (
    import_tax_step1,
    import_tax_step2,
    import_tax_step3,
    import_tax_sample,
    import_taxgroup_step1,
    import_taxgroup_step2,
    import_taxgroup_step3,
    import_taxgroup_sample,
)

urlpatterns = [
    path('add-tax-type/', views.add_tax_type, name='add_tax_type'),
    path('tax-type/add/modal/', views.tax_type_add_modal, name='tax_type_add_modal'),
    path('add/', views.add_tax, name='add_tax'),
    path('add-tax-group/', views.add_taxgrp, name='add_taxgrp'),
    path('tax-master/', views.tax_master_list, name='tax_master_list'),
    path('tax-master/add/', views.tax_master_add, name='tax_master_add'),
    path('tax-master/add/modal/', views.tax_master_add_modal, name='tax_master_add_modal'),
    path('tds-master/add/modal/', views.tds_master_add_modal, name='tds_master_add_modal'),
    path('tcs-master/add/modal/', views.tcs_master_add_modal, name='tcs_master_add_modal'),
    path('tax-master/modal/', views.tax_master_modal_list, name='tax_master_modal_list'),
    path('tds-master/modal/', views.tds_master_modal_list, name='tds_master_modal_list'),
    path('tcs-master/modal/', views.tcs_master_modal_list, name='tcs_master_modal_list'),
    path('tds-master/<int:pk>/edit/modal/', views.tds_master_edit_modal, name='tds_master_edit_modal'),
    path('tcs-master/<int:pk>/edit/modal/', views.tcs_master_edit_modal, name='tcs_master_edit_modal'),
    path('tax-master/<int:pk>/edit/', views.tax_master_edit, name='tax_master_edit'),
    path('tax-master/<int:pk>/delete/', views.tax_master_delete, name='tax_master_delete'),
    path('', views.tax_list, name='tax_list'),
    path('tax/<int:pk>/edit/', views.tax_edit, name='tax_edit'),
    path('tax/<int:pk>/delete/', views.tax_delete, name='tax_delete'),
    path('tax/add/modal/', views.tax_add_modal, name='tax_add_modal'),
    path('taxgroup/edit/<int:pk>/', views.edit_taxgrp, name='edit_taxgrp'),
    path('taxgroup/delete/<int:pk>/', views.taxgrp_delete, name='taxgrp_delete'),
    path('tax-choices-partial/', views.tax_choices_partial, name='tax_choices_partial'),

    #import and export urls
    path('import_tax/', import_tax_step1, name='import_tax_step1'),
    path('import_tax/step2/', import_tax_step2, name='import_tax_step2'),
    path('import_tax/step3/', import_tax_step3, name='import_tax_step3'),
    path('import_tax/sample/', import_tax_sample, name='import_tax_sample'),

    path('import_taxgroup/', import_taxgroup_step1, name='import_taxgroup_step1'),
    path('import_taxgroup/step2/', import_taxgroup_step2, name='import_taxgroup_step2'),
    path('import_taxgroup/step3/', import_taxgroup_step3, name='import_taxgroup_step3'),
    path('import_taxgroup/sample/', import_taxgroup_sample, name='import_taxgroup_sample'),
]