# from django.contrib import admin
# from .models import Bank, BankReconciliation, BankReconciliationLine, BankStatementLine
# from .models import BankRule


# @admin.register(Bank)
# class BankAdmin(admin.ModelAdmin):
#     list_display = ['bank_name', 'status', 'created_at']
#     list_filter = ['status', 'created_at']
#     search_fields = ['bank_name']
#     readonly_fields = ['created_at', 'updated_at']


# @admin.register(BankReconciliation)
# class BankReconciliationAdmin(admin.ModelAdmin):
#     list_display = ['bank_account', 'end_date', 'status', 'closing_balance', 'cleared_amount', 'difference']
#     list_filter = ['status', 'end_date', 'bank_account']
#     search_fields = ['bank_account__account_number']
#     readonly_fields = ['created_at', 'updated_at', 'created_by', 'cleared_amount', 'difference']
#     fieldsets = (
#         ('Account Info', {
#             'fields': ('bank_account', 'start_date', 'end_date')
#         }),
#         ('Balances', {
#             'fields': ('closing_balance', 'cleared_amount', 'difference')
#         }),
#         ('Status', {
#             'fields': ('status', 'reconciled_date')
#         }),
#         ('Attachment', {
#             'fields': ('attachment',),
#             'classes': ('collapse',)
#         }),
#         ('Audit', {
#             'fields': ('created_at', 'created_by', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )


# @admin.register(BankReconciliationLine)
# class BankReconciliationLineAdmin(admin.ModelAdmin):
#     list_display = ['get_reconciliation', 'transaction_date', 'description', 'debit_amount', 'credit_amount', 'is_cleared', 'auto_matched']
#     list_filter = ['is_cleared', 'auto_matched', 'transaction_date', 'transaction_type', 'reconciliation']
#     search_fields = ['description']
#     readonly_fields = ['created_at', 'auto_matched']
#     date_hierarchy = 'transaction_date'
    
#     def get_reconciliation(self, obj):
#         return obj.reconciliation
#     get_reconciliation.short_description = 'Reconciliation'


# @admin.register(BankStatementLine)
# class BankStatementLineAdmin(admin.ModelAdmin):
#     list_display = ['statement_date', 'description', 'debit_amount', 'credit_amount', 'match_status', 'get_bank']
#     list_filter = ['match_status', 'statement_date', 'bank_account', 'reconciliation']
#     search_fields = ['description', 'reference']
#     readonly_fields = ['created_at']
#     date_hierarchy = 'statement_date'
    
#     def get_bank(self, obj):
#         return obj.bank_account
#     get_bank.short_description = 'Bank Account'


# @admin.register(BankRule)
# class BankRuleAdmin(admin.ModelAdmin):
#     list_display = ['name', 'bank_account', 'pattern', 'amount_tolerance', 'date_window', 'active', 'auto_match']
#     list_filter = ['bank_account', 'active', 'auto_match']
#     search_fields = ['name', 'pattern']
#     readonly_fields = ['created_at']
