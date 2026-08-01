from django.contrib import admin

from .models import Type


@admin.register(Type)
class TypeAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'subcategory', 'status')
    search_fields = ('type_name', 'subcategory__subcategory_name')
    list_filter = ('status', 'subcategory')
