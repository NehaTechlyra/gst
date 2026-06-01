from django.db import models
from bank.models import Bank  
from company.models import Company
from django.conf import settings
from django_countries.fields import CountryField
from chart_of_accounts.models import ChartOfAccounts

class CompanyBankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_bank_accounts")
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, related_name="bank_accounts")

    account_name = models.CharField(max_length=255, help_text="Account Holder Name")
    account_number = models.CharField(max_length=50)
    ifsc_swift_code = models.CharField(max_length=50, blank=True, null=True)
    chart_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_bank_accounts",
        help_text="Ledger entry that tracks this bank account"
    )

    branch_name = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="company_bank_created",
                                   null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="company_bank_updated",
                                   null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["bank__bank_name", "account_name"]

    def __str__(self):
        return f"{self.bank.bank_name} - {self.account_number}"




class LocationType(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="locations")
    location_type = models.ForeignKey(LocationType, on_delete=models.PROTECT, related_name="locations")

    # Basic Info
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)

    # Additional dynamic info (optional based on type)
    # display_capacity = models.CharField(max_length=100, blank=True, null=True)
    # storage_capacity = models.CharField(max_length=100, blank=True, null=True)
    # gps_location = models.CharField(max_length=255, blank=True, null=True)
    # certification_number = models.CharField(max_length=100, blank=True, null=True)
    # service_capabilities = models.TextField(blank=True, null=True)

    # Manager Info
    manager_name = models.CharField(max_length=255, blank=True, null=True)
    manager_phone = models.CharField(max_length=50, blank=True, null=True)
    manager_email = models.EmailField(blank=True, null=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = CountryField(blank=True, null=True)
    postal_code = models.CharField(max_length=20)

    # Contact
    phone = models.CharField(max_length=50, blank=True, null=True)
    working_hours = models.CharField(max_length=255, blank=True, null=True)

    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="location_created",
                                   null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="location_updated",
                                   null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} ({self.location_type})"



from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class LicenseKey(models.Model):
    """
    License key for a company (synced from generator app)
    This is the ERP-side record of activated licenses
    """
    
    company = models.OneToOneField(
        'company.Company',  # Make sure this references your Company model
        on_delete=models.CASCADE,
        related_name="license"
    )

    license_key = models.CharField(
        max_length=255, 
        unique=True,
        help_text="License key from generator app"
    )
    
    # Company GST (synced from generator)
    company_gst = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Company GST number from license"
    )
    
    # Company PAN (extracted from GST)
    company_pan = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="PAN extracted from GST"
    )
    
    # Dates
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Limits (synced from generator)
    max_users = models.IntegerField(default=10)
    max_locations = models.IntegerField(default=5, null=True, blank=True)
    
    # Module access - synced from generator
    module_access = models.JSONField(default=dict, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    #  Version Control Fields
    erp_version = models.CharField(
        max_length=20,
        default="1.0.0",
        help_text="ERP version this license is valid for (e.g., 1.0.0, 2.1.5)"
    )
    
    license_version = models.PositiveIntegerField(
        default=1,
        help_text="Internal license schema version"
    )

    # Activation tracking
    activated_at = models.DateTimeField(null=True, blank=True)
    activation_ip = models.GenericIPAddressField(null=True, blank=True)

    # Email tracking for license expiry notifications
    license_expired_email_last_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last 'license expired' email was sent"
    )

    # License Expiration Status Flag
    is_license_expired = models.BooleanField(
        default=False,
        help_text="Set to True at 12:00 AM on the DAY AFTER expiry_date. "
                  "E.g., if expiry_date=2026-02-25, this becomes True on 2026-02-26 at 00:00. "
                  "Used for all expiry checks (emails, activation, module access, etc.)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "License Key"
        verbose_name_plural = "License Keys"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company.name} - {self.license_key}"

    # =========================
    # Status Checks
    # =========================
    def is_expired(self):
        """
        Check if license has expired using is_license_expired flag.
        This flag is set to True at 12:00 AM on the expiry date.
        """
        return self.is_license_expired

    def days_remaining(self):
        """Calculate days remaining until expiry (computed, not stored)"""
        if not self.expiry_date:
            return None
        
        today = timezone.now().date()
        if self.expiry_date < today:
            return 0
        
        delta = self.expiry_date - today
        return delta.days

    # =========================
    # Module Access
    # =========================
    def has_module_access(self, module_code):
        """Check if license has access to specific module"""
        if not self.module_access:
            return False
        
        # Core modules are always accessible if license is valid
        try:
            from .constants import get_module_by_code
            module = get_module_by_code(module_code)
            if module and module.get('is_core', False):
                return True
        except (ImportError, AttributeError):
            pass
        
        return self.module_access.get(module_code, False)

    def get_enabled_modules(self):
        """Get list of enabled module codes"""
        if not self.module_access:
            return []
        
        return [code for code, access in self.module_access.items() if access]

    # =========================
    # Display Methods
    # =========================
    def get_status_display(self):
        """Get human-readable status"""
        if not self.is_active:
            return "Inactive"
        elif self.is_license_expired:
            return "Expired"
        else:
            return "Active"

    def get_license_info(self):
        """Export license information as dictionary"""
        return {
            'license_key': self.license_key,
            'company_gst': self.company_gst,
            'company_pan': self.company_pan,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_remaining': self.days_remaining(),
            'is_expired': self.is_expired(),
            'is_active': self.is_active,
            'max_users': self.max_users,
            'max_locations': self.max_locations,
            'module_access': self.module_access or {},
            'erp_version': self.erp_version,  
            'license_version': self.license_version,
            'status': self.get_status_display(),
        }

    def mark_license_expired_email_sent(self):
        """
        Mark that a license-expired email was sent (for rate limiting).
        """
        from django.utils import timezone

        self.license_expired_email_last_sent = timezone.now()
        self.save(update_fields=['license_expired_email_last_sent'])
    
    def is_version_compatible(self, client_erp_version):
        """
        Check if client ERP version matches license ERP version.
        Returns True only for EXACT match.
        """
        if not client_erp_version or not self.erp_version:
            return False
        
        try:
            from packaging import version
            client_ver = version.parse(client_erp_version)
            license_ver = version.parse(self.erp_version)
            return client_ver == license_ver
        except Exception:
            return str(client_erp_version).strip() == str(self.erp_version).strip()
