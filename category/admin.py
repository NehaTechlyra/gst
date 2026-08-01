from django.contrib import admin

from .models import Category, Subcategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'status')
    search_fields = ('category_name',)
    list_filter = ('status',)


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('subcategory_name', 'category', 'status')
    search_fields = ('subcategory_name', 'category__category_name')
    list_filter = ('status', 'category')
