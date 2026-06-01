from django.urls import path

from . import views

app_name = "currencies"

urlpatterns = [
    path("", views.currency_list, name="currency_list"),
    path("add/", views.currency_add, name="currency_add"),
    path("<int:pk>/edit/", views.currency_edit, name="currency_edit"),
    path("<int:pk>/delete/", views.currency_delete, name="currency_delete"),
    path("<int:pk>/rates/", views.exchange_rate_list, name="exchange_rate_list"),
    path("<int:pk>/rates/add/", views.exchange_rate_add, name="exchange_rate_add"),
    path("rates/<int:rate_id>/delete/", views.exchange_rate_delete, name="exchange_rate_delete"),
    path("feeds/toggle/", views.toggle_exchange_feeds, name="toggle_exchange_feeds"),
    # path("feeds/toggle/", views.toggle_exchange_feeds, name="toggle_exchange_feeds"),
    path("api/vendor_rate/", views.api_get_vendor_currency, name="api_get_vendor_currency"),
    path("api/customer_rate/", views.api_get_customer_currency, name="api_get_customer_currency"),
]
