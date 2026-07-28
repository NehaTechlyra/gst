# from django.contrib import admin
# from .models import PriceList, PriceListItem, ContactPriceList


# class PriceListItemInline(admin.TabularInline):
#     model = PriceListItem
#     extra = 1
#     fields = ['item_name', 'item_sku', 'unit', 'base_price',
#               'discount_type', 'discount_value', 'custom_price', 'min_quantity']
#     readonly_fields = []


# @admin.register(PriceList)
# class PriceListAdmin(admin.ModelAdmin):
#     list_display = ['name', 'price_type', 'currency', 'is_active',
#                     'valid_from', 'valid_to', 'get_item_count', 'created_at']
#     list_filter = ['price_type', 'is_active', 'currency']
#     search_fields = ['name', 'description']
#     inlines = [PriceListItemInline]
#     readonly_fields = ['created_at', 'updated_at']

#     @admin.display(description='Items')
#     def get_item_count(self, obj):
#         return obj.get_item_count()


# @admin.register(PriceListItem)
# class PriceListItemAdmin(admin.ModelAdmin):
#     list_display = ['item_name', 'item_sku', 'price_list', 'base_price',
#                     'discount_type', 'discount_value', 'final_price']
#     list_filter = ['price_list', 'discount_type']
#     search_fields = ['item_name', 'item_sku']
#     readonly_fields = ['final_price', 'created_at', 'updated_at']

#     @admin.display(description='Final Price')
#     def final_price(self, obj):
#         return obj.final_price


# @admin.register(ContactPriceList)
# class ContactPriceListAdmin(admin.ModelAdmin):
#     list_display = ['contact_name', 'contact_type', 'price_list', 'created_at']
#     list_filter = ['contact_type']
#     search_fields = ['contact_name']
