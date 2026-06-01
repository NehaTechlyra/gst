from django.contrib import admin


from .models import Supplier, Product, PurchaseOrder
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(PurchaseOrder)
