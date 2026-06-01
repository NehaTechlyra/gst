from django.contrib import admin
from .models import Expense, ExpenseLine, Vendor
from Tax.models import Tax

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name','contact','email')

@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ('taxname','taxtype','rate')

class ExpenseLineInline(admin.TabularInline):
    model = ExpenseLine
    extra = 0

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'vendor', 'total_amount', 'currency')
    inlines = [ExpenseLineInline]