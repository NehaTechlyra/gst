"""
migration_status_urls.py
------------------------
Register in your ROOT urls.py (not inside the company-code prefix):

    from django.urls import path, include

    urlpatterns = [
        ...
        path('_migration_status/', include('Lyraerp.migration_status_urls')),
        ...
    ]
"""
from django.urls import path
from . import migration_status_view

urlpatterns = [
    path('', migration_status_view.migration_status, name='migration_status'),
]