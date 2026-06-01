from django import forms
from django.db import OperationalError
from django.db.models import Q


def world_locations_ready():
    try:
        from cities_light.models import Country

        return Country.objects.exists()
    except OperationalError:
        return False


def country_code_from_value(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value.isdigit():
        try:
            from cities_light.models import Country

            country = Country.objects.filter(pk=int(value)).first()
            return (country.code2 if country else "").upper()
        except (OperationalError, ValueError):
            return ""

    try:
        from cities_light.models import Country

        country = Country.objects.filter(code2__iexact=value).first()
        if not country:
            country = Country.objects.filter(name__iexact=value).first()
        if country:
            return (country.code2 or "").upper()
    except OperationalError:
        pass

    return value.upper()


def resolve_location_value(value, model):
    value = (value or "").strip()
    if not value:
        return ""

    if value.isdigit():
        try:
            obj = model.objects.filter(pk=int(value)).first()
            if obj:
                return obj.display_name or obj.name
        except (OperationalError, TypeError, ValueError):
            return value

    return value


def find_region_id(country_code, state_name):
    country_code = country_code_from_value(country_code)
    state_name = (state_name or "").strip()
    if not country_code or not state_name:
        return ""

    try:
        from cities_light.models import Region

        region = (
            Region.objects.filter(country__code2=country_code)
            .filter(Q(name__iexact=state_name) | Q(display_name__iexact=state_name))
            .first()
        )
        return str(region.pk) if region else ""
    except OperationalError:
        return ""


def location_select_choice(value, empty_label):
    value = (value or "").strip()
    choices = [("", empty_label)]
    if value:
        choices.append((value, value))
    return choices


def configure_location_fields(form, country_field, state_field, city_field, *, shipping=False):
    country_value = ""
    state_value = ""
    city_value = ""

    if form.is_bound:
        country_value = form.data.get(country_field, "")
        state_value = form.data.get(state_field, "")
        city_value = form.data.get(city_field, "")
    else:
        instance = getattr(form, "instance", None)
        country_value = getattr(instance, country_field, "") if instance else ""
        state_value = getattr(instance, state_field, "") if instance else ""
        city_value = getattr(instance, city_field, "") if instance else ""

    state_id = find_region_id(country_value, state_value)
    prefix = "shipping " if shipping else ""

    form.fields[state_field].widget = forms.Select(
        choices=location_select_choice(state_value, f"Select {prefix}state".title()),
        attrs={
            "class": "form-control select2 location-state-select",
            "data-country-field": f"id_{country_field}",
            "data-city-field": f"id_{city_field}",
            "data-initial-state-id": state_id,
        },
    )
    form.fields[city_field].widget = forms.Select(
        choices=location_select_choice(city_value, f"Select {prefix}city".title()),
        attrs={
            "class": "form-control select2 location-city-select",
            "data-country-field": f"id_{country_field}",
            "data-state-field": f"id_{state_field}",
            "data-initial-value": city_value,
        },
    )
