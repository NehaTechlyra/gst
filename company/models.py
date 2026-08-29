"""
Company Model with 30-Day Trial System
Integrated with existing LicenseKey model from company_settings

DUAL DB SYNC: All trial fields and contact person fields are synced
to both master DB and company DB automatically.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
import base64
import re
import logging
from datetime import datetime, timedelta
from django_countries.fields import CountryField

logger = logging.getLogger(__name__)


class Company(models.Model):
    # ============================================================================
    # BASIC INFO
    # ============================================================================
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)

    # ============================================================================
    # ADDRESS
    # ============================================================================
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = CountryField(blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # ============================================================================
    # CONTACT
    # ============================================================================
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # ============================================================================
    # LOGO
    # ============================================================================
    logo = models.ImageField(upload_to="company/logos/", blank=True, null=True)
    logo_base64 = models.TextField(blank=True, null=True)
    show_logo_in_print_pdf = models.BooleanField(default=False)


    # ============================================================================
    # PRIMARY CONTACT PERSON
    # ============================================================================
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)

    # ============================================================================
    # FINANCIAL & TAX
    # ============================================================================
    TAX_TYPE_CHOICES = [
        ("GST", "GST"),
        ("VAT", "VAT"),
        ("SALES", "SALES"),
        ("TURNOVER", "TURNOVER"),
        ("NONE", "NONE"),
    ]
    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, default="GST")
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    # Allow base_currency to be blank/NULL and do not force a default —
    # admin should explicitly set the organisation base currency.
    base_currency = models.CharField(max_length=10, blank=True, null=True)
    fiscal_year_start = models.DateField(blank=True, null=True)
    REPORT_BASIS_CHOICES = [
        ("accrual", "Accrual – Tax at Invoice Date"),
        ("cash", "Cash – Tax at Payment Receipt")
    ]
    report_basis = models.CharField(max_length=10, choices=REPORT_BASIS_CHOICES, default="accrual")

    # ============================================================================
    # SOCIAL LINKS
    # ============================================================================
    facebook = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    # ============================================================================
    # MISC
    # ============================================================================
    additional_information = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)

    # Allow automatic exchange rate feeds to be enabled per company
    exchange_rate_feeds_enabled = models.BooleanField(
        default=False,
        help_text="When enabled, scheduled fetches will populate ExchangeRate rows from configured feeds",
    )

    # Per-company toggle: control whether stock is managed on delivery or on payment
    stock_management_on_delivery = models.BooleanField(
        default=True,
        help_text=(
            "When True: stock quantities are updated only when a Delivery is processed. "
            "When False: stock quantities are updated when payment is recorded for purchase/sales."
        ),
    )
    auto_load_cash_customer = models.BooleanField(
        default=False,
        help_text="Automatically select the Cash Customer when creating new sales quotations, orders, invoices, or performa invoices.",
    )

    show_base_transaction_summary = models.BooleanField(
        default=True,
        help_text="If enabled, show the base transaction summary block (div#base-transaction-summary) in relevant pages.",
    )

    PRINT_PAPER_SIZE_CHOICES = [
        ("A4", "A4"),
        ("POS", "POS / EPOS"),
    ]
    print_paper_size = models.CharField(
        max_length=20,
        choices=PRINT_PAPER_SIZE_CHOICES,
        default="A4",
        help_text="Preferred paper size for printing documents.",
    )

    # ============================================================================
    # SETUP TRACKING
    # ============================================================================
    setup_complete = models.BooleanField(
        default=False,
        help_text="Indicates if initial company setup is complete"
    )

    setup_checklist_shown = models.BooleanField(
    default=False,
    help_text="Has the post-setup checklist been shown to the user once?"
    )

    # ============================================================================
    # DATABASE
    # ============================================================================
    db_name = models.CharField(max_length=100, unique=True, null=True, blank=True)

    db_created = models.BooleanField(
        default=False,
        help_text="Has the company database been created?"
    )

    first_login_completed = models.BooleanField(
        default=False,
        help_text="Has the first login/database creation completed?"
    )

    # ============================================================================
    # COMPANY CODE
    # ============================================================================
    company_code = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Auto-generated code in format: COMPANYNAME-YEAR (e.g., TECHSOLUTIONS-2025)"
    )

    # ============================================================================
    # TRIAL SYSTEM FIELDS
    # ============================================================================

    trial_active = models.BooleanField(
        default=True,
        help_text="Is the company currently in trial mode?"
    )

    trial_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was the trial created (signup date)?"
    )

    trial_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When did the trial start? (same as signup date now)"
    )

    trial_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When does the trial expire? (trial_started_at + 30 days)"
    )

    trial_reminder_sent = models.BooleanField(
        default=False,
        help_text="Has the day-10 reminder email been sent?"
    )

    trial_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was the trial reminder email sent?"
    )

    trial_expired_email_last_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was the last trial expired email sent? (sent every 3 days)"
    )

    is_trial_expired = models.IntegerField(
        default=0,
        help_text="Flag: 1 = trial expired, 0 = trial active/not expired"
    )

    # ============================================================================
    # AUDIT
    # ============================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="company_created",
        on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="company_updated",
        on_delete=models.SET_NULL
    )

    # ============================================================================
    # SAVE METHOD
    # ============================================================================
    def save(self, *args, **kwargs):
        using = kwargs.get('using') or 'default'
        update_fields = kwargs.get('update_fields')

        # ADD THIS - trace every save call
        import traceback
        logger.warning(
            "[COMPANY SAVE] pk=%s name=%s tax_type='%s' update_fields=%s using=%s\nStack:\n%s",
            self.pk,
            self.name,
            self.tax_type,
            update_fields,
            using,
            ''.join(traceback.format_stack(limit=8))
        )

        if not self.company_code:
            self.company_code = self._generate_company_code()

        if self.logo:
            try:
                with self.logo.open("rb") as logo_file:
                    self.logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
            except Exception:
                pass

        super().save(*args, **kwargs)

        # Keep company DB in sync for writes performed in master DB.
        if using == 'default':
            if update_fields:
                self._sync_fields_to_company_db(list(update_fields))
            elif self.db_created:
                # Full save path (no update_fields): sync full record.
                try:
                    from Lyraerp.utils.db_utils import sync_company_record
                    sync_company_record(self)
                except Exception as exc:
                    logger.warning(
                        "[SYNC] Full company sync after save failed for '%s': %s",
                        self.name,
                        exc,
                    )

    # ============================================================================
    # COMPANY CODE GENERATION
    # ============================================================================
    def _generate_company_code(self):
        """Format: COMPANYNAME-YEAR e.g. TECHSOLUTIONS-2025"""
        year = datetime.now().year
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', self.name).upper()[:15]
        base_code = f"{clean_name}-{year}"
        code = base_code
        counter = 2

        while Company.objects.filter(company_code=code).exists():
            code = f"{base_code}-{counter}"
            counter += 1
            if counter > 100:
                import time
                code = f"{clean_name}-{int(time.time())}"
                break

        return code

    # ============================================================================
    # DUAL DB SYNC HELPER
    # ============================================================================

    def _sync_fields_to_company_db(self, fields):
        """
        Sync specific fields to company DB using .update() to avoid
        triggering the full save() pipeline (logo re-encoding, code regen, etc.)

        Only runs if:
        - db_name is set
        - db_created is True
        - The company record exists in company DB (uses update_or_create fallback)
        """
        if not self.db_name or not self.db_created:
            logger.debug(
                f"[SYNC] Skipping company DB sync for '{self.name}' — "
                f"db_name={self.db_name}, db_created={self.db_created}"
            )
            return

        try:
            from Lyraerp.utils.db_utils import register_database
            register_database(self.db_name)

            field_values = {field: getattr(self, field) for field in fields}

            updated = Company.objects.using(self.db_name).filter(pk=self.pk).update(
                **field_values
            )

            if updated == 0:
                # Row doesn't exist yet in company DB — create it
                logger.warning(
                    f"[SYNC] Company pk={self.pk} not found in {self.db_name}. "
                    f"Creating record via sync_company_record()."
                )
                self._ensure_company_record_in_company_db()
                # Retry update
                Company.objects.using(self.db_name).filter(pk=self.pk).update(
                    **field_values
                )
            else:
                logger.debug(
                    f"[SYNC] Synced fields {fields} to {self.db_name} for company '{self.name}'"
                )

        except Exception as e:
            logger.warning(
                f"[SYNC] Could not sync fields {fields} to {self.db_name} "
                f"for company '{self.name}': {e}"
            )

    def _ensure_company_record_in_company_db(self):
        """
        Ensures a Company row exists in the company DB.
        Copies all non-relational fields from the current instance.
        Called automatically by _sync_fields_to_company_db if row is missing.
        """
        try:
            # Build field dict excluding auto fields and FK fields
            skip_fields = {
                'created_at', 'updated_at', 'created_by', 'updated_by',
                'created_by_id', 'updated_by_id',
            }
            field_values = {}
            for f in self._meta.fields:
                if f.name in skip_fields:
                    continue
                if f.primary_key:
                    continue
                field_values[f.attname] = getattr(self, f.attname)

            Company.objects.using(self.db_name).update_or_create(
                id=self.pk,
                defaults=field_values
            )
            logger.info(
                f"[SYNC] Created Company record in {self.db_name} for '{self.name}'"
            )
        except Exception as e:
            logger.error(
                f"[SYNC] Failed to ensure Company record in {self.db_name}: {e}",
                exc_info=True
            )

    def sync_contact_person_to_master(self):
        """
        Sync contact person fields from company DB → master DB.
        Call this after updating contact person details that were saved
        directly to the company DB during signup.
        """
        fields = ['contact_person', 'contact_email', 'contact_phone']
        try:
            Company.objects.using('default').filter(pk=self.pk).update(
                **{field: getattr(self, field) for field in fields}
            )
            logger.info(
                f"[SYNC] Synced contact person to master DB for '{self.name}'"
            )
        except Exception as e:
            logger.warning(
                f"[SYNC] Could not sync contact person to master DB for '{self.name}': {e}"
            )
        except Exception as e:
                logger.warning(
                    f"[SYNC] Could not sync contact person to master DB for '{self.name}': {e}"
                )

    def save_contact_person(self, contact_person, contact_email, contact_phone):
        """
        Save contact person details to BOTH master and company DB.

        Use this method whenever updating contact person details to ensure
        both databases stay in sync.

        Args:
            contact_person: Full name of contact person
            contact_email: Email of contact person
            contact_phone: Phone of contact person
        """
        self.contact_person = contact_person
        self.contact_email = contact_email
        self.contact_phone = contact_phone

        fields = ['contact_person', 'contact_email', 'contact_phone']

        # Save to master DB
        Company.objects.using('default').filter(pk=self.pk).update(
            contact_person=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )
        logger.info(f"[CONTACT] Saved contact person to master DB for '{self.name}'")

        # Save to company DB
        self._sync_fields_to_company_db(fields)
        logger.info(f"[CONTACT] Saved contact person to company DB for '{self.name}'")

    # ============================================================================
    # TRIAL MANAGEMENT METHODS
    # ============================================================================

    def activate_trial(self):
        """
        Called at signup.
        Sets trial_active = True and records trial_created_at.
        Saves to BOTH master DB and company DB.
        """
        self.trial_active = True
        self.trial_created_at = datetime.now()

        fields = ['trial_active', 'trial_created_at']

        # Always save to master DB explicitly
        self.save(using='default', update_fields=fields)
        logger.info(f"[TRIAL] activate_trial saved to master DB for '{self.name}'")

        # Sync to company DB if ready
        self._sync_fields_to_company_db(fields)

    def start_trial(self):
        """
        Called at signup (immediately after activate_trial).
        Starts the 30-day countdown from signup date.
        Has an internal guard so it never overwrites an existing start date.
        Saves to BOTH master DB and company DB.
        """
        if not self.trial_started_at:
            self.trial_started_at = datetime.now()
            self.trial_expires_at = self.trial_started_at + timedelta(days=30)

            fields = ['trial_started_at', 'trial_expires_at']

            # Always save to master DB explicitly
            self.save(using='default', update_fields=fields)
            logger.info(f"[TRIAL] start_trial saved to master DB for '{self.name}'")

            # Sync to company DB if ready
            self._sync_fields_to_company_db(fields)

    def check_trial_expired(self):
        """
        Returns True if trial has passed its expiry date AND no valid license exists.
        
        CRITICAL: is_trial_expired flag is ALWAYS updated based on trial dates,
        regardless of whether a valid license is present.
        
        This allows tracking:
        - Whether trial period has ended (independent of license status)
        - Once set to 1, it NEVER resets to 0 (permanent historical record)
        
        Access control logic:
        - Trial expired + No license: BLOCKED (show trial_expired.html)
        - Trial expired + Valid license: ALLOWED (license provides access)
        - License expired + Trial ended: BLOCKED (show license_expired.html)
        """
        if not self.trial_started_at or not self.trial_expires_at:
            return False
        
        # Treat the expiry date as inclusive: the company keeps access
        # throughout the expiry date and becomes expired at 00:00 of the
        # following day. This makes an expiry_date of 25th expire at
        # 26th 00:00 (i.e. when current date > expiry_date).
        now = timezone.now()
        try:
            expires_date = self.trial_expires_at.date()
            is_expired = now.date() > expires_date
        except Exception:
            # Fallback: attempt to compare dates first, then datetimes.
            try:
                is_expired = now.date() > self.trial_expires_at.date()
            except Exception:
                is_expired = now >= self.trial_expires_at
        
        # ── CRITICAL: Update flag based on trial dates REGARDLESS of license ──
        # is_trial_expired tracks whether the trial period has ended (historical)
        # Once set to 1, it NEVER resets to 0
        if is_expired:
            if self.is_trial_expired != 1:
                self.is_trial_expired = 1
                self.save(using='default', update_fields=['is_trial_expired'])
                logger.info(
                    f"[TRIAL] Trial expired for '{self.name}' — is_trial_expired set to 1 "
                    f"(trial_expires_at: {self.trial_expires_at}, "
                    f"has_license: {bool(self.has_valid_license())})"
                )
        # ── DO NOT reset to 0: is_trial_expired=1 is permanent once set ──
        # Even if license is activated, trial expiration date stays marked
        
        return is_expired

    def days_until_trial_expires(self):
        """
        Returns days remaining (negative if already expired).
        Returns None if trial has not started.
        """
        if not self.trial_expires_at:
            return None
        return (self.trial_expires_at - timezone.now()).days

    def should_send_trial_reminder(self):
        """
        Returns True if the day-10 reminder email should be sent.
        Fires once: on day 10 or later if somehow missed.
        """
        if self.trial_reminder_sent:
            return False
        if not self.trial_started_at:
            return False
        days_passed = (timezone.now() - self.trial_started_at).days
        # Change: send reminder on day 10 or later (i.e., after 10 full days)
        return days_passed >= 10

    def mark_trial_reminder_sent(self):
        """
        Mark that the day-10 reminder has been sent.
        Saves to BOTH master DB and company DB.
        """
        self.trial_reminder_sent = True
        self.trial_reminder_sent_at = timezone.now()

        fields = ['trial_reminder_sent', 'trial_reminder_sent_at']

        self.save(using='default', update_fields=fields)
        logger.info(f"[TRIAL] mark_trial_reminder_sent saved to master DB for '{self.name}'")

        self._sync_fields_to_company_db(fields)

    def should_send_trial_expired_email(self):
        # Trial not expired yet
        if not self.is_trial_expired:        # ← was: self.is_trial_expired()
            return False

        # Company has a valid license — stop sending
        if self.has_valid_license():
            return False

        # Never sent before — send now
        if not self.trial_expired_email_last_sent:
            return True

        # Only send again after 72 hours (3 days) have passed
        hours_since_last = (
            timezone.now() - self.trial_expired_email_last_sent
        ).total_seconds() / 3600

        return hours_since_last >= 72

    def mark_trial_expired_email_sent(self):
        """
        Mark that an expired email was sent and reset the 72-hour window.
        Saves to BOTH master DB and company DB.
        """
        self.trial_expired_email_last_sent = timezone.now()

        fields = ['trial_expired_email_last_sent']

        self.save(using='default', update_fields=fields)
        logger.info(
            f"[TRIAL] mark_trial_expired_email_sent saved to master DB for '{self.name}'"
        )

        self._sync_fields_to_company_db(fields)

    # ============================================================================
    # LICENSE MANAGEMENT METHODS
    # ============================================================================

    def has_valid_license(self):
        """Returns True if company has an active, non-expired license."""
        try:
            license_obj = self.license
            if not license_obj or not license_obj.is_active:
                return False
            if license_obj.is_expired():
                return False
            return True
        except Exception:
            return False

    def get_license_info(self):
        """Returns license info dict from LicenseKey model, or None."""
        try:
            license_obj = self.license
            if license_obj:
                return license_obj.get_license_info()
        except Exception:
            pass
        return None

    def activate_license_key(self, license_key_string):
        """
        Activate a license key for the company.
        Also deactivates trial and syncs to company DB.
        Returns (success: bool, message: str).
        """
        try:
            from company_settings.models import LicenseKey

            if not license_key_string or len(license_key_string) < 10:
                return False, "Invalid license key format"

            try:
                license_obj = self.license
                license_obj.license_key = license_key_string
                license_obj.is_active = True
                license_obj.activated_at = datetime.now()
                license_obj.save()
            except LicenseKey.DoesNotExist:
                LicenseKey.objects.create(
                    company=self,
                    license_key=license_key_string,
                    is_active=True,
                    activated_at=datetime.now()
                )

            # Deactivate trial in both DBs
            self.trial_active = False
            fields = ['trial_active']
            self.save(using='default', update_fields=fields)
            self._sync_fields_to_company_db(fields)

            logger.info(
                f"[LICENSE] License activated and trial deactivated "
                f"in both DBs for '{self.name}'"
            )

            return True, "License activated successfully!"

        except Exception as e:
            return False, f"Error activating license: {str(e)}"

    # ============================================================================
    # STRING REPRESENTATION & META
    # ============================================================================

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['-created_at']


# Ensure a Currency row exists for a company's base currency whenever the company is saved.
def _ensure_company_base_currency_row(sender, instance, **kwargs):
    try:
        code = (getattr(instance, 'base_currency', None) or '').strip().upper()[:3]
        if not code:
            return
        # Import here to avoid circular imports at module load time
        from currencies.models import Currency

        # Resolve better symbol/name using currencies utilities when available
        try:
            from currencies.utils import get_currency_symbol, get_currency_name
            symbol = get_currency_symbol(code) or code
            name = get_currency_name(code) or code
        except Exception:
            symbol = code
            name = code

        cur, created = Currency.objects.get_or_create(
            company=instance,
            code=code,
            defaults={
                'symbol': symbol,
                'name': name,
                'decimal_places': 2,
                'is_base': True,
                'is_active': True,
            }
        )
        # Ensure only one base currency
        Currency.objects.filter(company=instance, is_base=True).exclude(pk=cur.pk).update(is_base=False)
        if not cur.is_base:
            cur.is_base = True
            cur.save(update_fields=['is_base'])
    except Exception:
        logger.warning(f"[CURRENCY SYNC] Could not ensure currency for company id={getattr(instance, 'id', 'N/A')}")


from django.db.models.signals import post_save
post_save.connect(_ensure_company_base_currency_row, sender=Company)
