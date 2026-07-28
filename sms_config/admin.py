# from django.contrib import admin
# from .models import SMSConfiguration, GSMModemConfig, MobileModemConfig, APIConfig


# class GSMModemConfigInline(admin.StackedInline):
#     model = GSMModemConfig
#     extra = 0
#     classes = ('gsm-fields',)
#     fieldsets = (
#         (None, {'fields': ('gsm_port', 'gsm_baudrate', 'gsm_timeout')}),
#     )


# class MobileModemConfigInline(admin.StackedInline):
#     model = MobileModemConfig
#     extra = 0
#     classes = ('mobile-fields',)
#     fieldsets = (
#         (None, {'fields': ('mobile_port',)}),
#     )


# class APIConfigInline(admin.StackedInline):
#     model = APIConfig
#     extra = 0
#     classes = ('api-fields',)
#     fieldsets = (
#         (None, {'fields': ('api_url', 'api_key', 'api_sender')}),
#     )


# @admin.register(SMSConfiguration)
# class SMSConfigurationAdmin(admin.ModelAdmin):
#     list_display = ("mode", "status", "updated_at")
#     inlines = [GSMModemConfigInline, MobileModemConfigInline, APIConfigInline]

#     fieldsets = (
#         (None, {
#             "fields": ("mode", "status", "created_by", "updated_by")
#         }),
#     )

#     class Media:
#         js = ("admin/js/sms_config_toggle.js",)
