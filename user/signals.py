import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model

from django.db import IntegrityError
from django.db.models.signals import post_save
from django.db.models import Q
from user.models import User
from sales.models import SalesPerson

logger = logging.getLogger(__name__)


@receiver(post_delete)
def sync_delete_to_master(sender, instance, using=None, **kwargs):
    """When a User row is deleted from a company DB, remove its master DB counterparts.

    This handler inspects the instance's database (instance._state.db). If the deletion
    occurred on a non-default database (i.e., a company DB), it will delete the matching
    records in the master (default) database:
      - `user.User` row matching `usr_name` and `company_id`
      - Django auth user matching `username`
    """
    try:
        # Only act for our User model (avoid catching deletions for unrelated models)
        UserModel = apps.get_model('user', 'User')
    except Exception:
        return

    if sender is not UserModel:
        return

    # Prefer the 'using' keyword from the signal if provided (reliable),
    # fall back to instance state.
    using_db = using or getattr(getattr(instance, '_state', None), 'db', None) or 'default'
    logger.debug("post_delete received for User '%s' from using='%s' (instance._state.db=%s)",
                 getattr(instance, 'usr_name', None), using, getattr(getattr(instance, '_state', None), 'db', None))
    if using_db == 'default':
        # Deletion happened in master DB already; nothing to sync
        logger.debug("Deletion from master DB — nothing to sync for %s", getattr(instance, 'usr_name', None))
        return

    try:
        # Delete master-level user record that was synced earlier (match by name and company)
        company_id = getattr(instance, 'company_id', None)
        UserModel.objects.using('default').filter(usr_name=instance.usr_name, company_id=company_id).delete()

        # Also remove the Django auth user in the master DB if present
        AuthUser = get_user_model()
        try:
            AuthUser.objects.using('default').filter(username=instance.usr_name).delete()
        except Exception:
            # Some projects might use a custom auth user model with different fields; ignore errors
            logger.debug("Failed to delete auth user for %s in master DB", instance.usr_name)

        logger.info("Synced deletion of user '%s' from %s to master DB", instance.usr_name, using_db)
    except Exception as exc:
        logger.exception("Error syncing user deletion to master DB: %s", exc)



@receiver(post_save, sender=User)
def create_salesperson_for_user(sender, instance, created, **kwargs):
    """Ensure a SalesPerson exists for every newly created User.

    - Runs only on created users.
    - Uses the same DB as the User instance when possible (multi-db/tenant-aware).
    - If a matching SalesPerson already exists (by email or exact name), update its contact fields.
    - Logs failures but does not interrupt user creation.
    """
    if not created:
        return

    logger.info("[SIGNAL FIRED] Creating/updating SalesPerson for user %s", getattr(instance, 'usr_name', None))
    try:
        db_alias = getattr(getattr(instance, '_state', None), 'db', None) or 'default'

        # Build matching criteria: prefer email, fall back to full name/username
        email = (getattr(instance, 'usr_mail', None) or '').strip() or None
        name_candidates = []
        try:
            fname = getattr(instance, 'usr_fname', None) or ''
            lname = getattr(instance, 'usr_lname', None) or getattr(instance, 'usr_lname', None) or getattr(instance, 'usr_name', '')
            full = ' '.join([p for p in (fname, lname) if p]).strip()
        except Exception:
            full = getattr(instance, 'usr_name', '') or ''
        if full:
            name_candidates.append(full)
        username = getattr(instance, 'usr_name', None) or getattr(instance, 'username', None)
        if username and username not in name_candidates:
            name_candidates.append(username)

        # Try to find existing SalesPerson by email or name in the same DB
        sp = None
        if email:
            sp = SalesPerson.objects.using(db_alias).filter(email__iexact=email).first()

        if not sp and name_candidates:
            # exact name match (case-insensitive)
            q = Q()
            for n in name_candidates:
                q |= Q(name__iexact=n)
            sp = SalesPerson.objects.using(db_alias).filter(q).first()

        # Create or update
        if sp:
            changed = False
            # update email/phone if missing or different
            if email and (not getattr(sp, 'email', None) or sp.email.lower() != email.lower()):
                sp.email = email
                changed = True
            phone = getattr(instance, 'usr_phn', None) or getattr(instance, 'phone', None)
            if phone and (not getattr(sp, 'phone', None) or str(sp.phone).strip() != str(phone).strip()):
                sp.phone = phone
                changed = True
            if changed:
                try:
                    sp.save(using=db_alias)
                    logger.info("[SALESPERSON UPDATED] id=%s on db=%s", sp.pk, db_alias)
                except Exception:
                    logger.exception("Failed to update SalesPerson for user %s", getattr(instance, 'usr_name', None))
        else:
            # create new SalesPerson
            try:
                SalesPerson.objects.using(db_alias).create(
                    name=full or (username or ''),
                    email=email,
                    phone=(getattr(instance, 'usr_phn', None) or getattr(instance, 'phone', None) or None),
                )
                logger.info("[SALESPERSON CREATED] for user %s on db=%s", getattr(instance, 'usr_name', None), db_alias)
            except IntegrityError:
                # Unique constraint on email or similar — try without email to avoid crash
                try:
                    SalesPerson.objects.using(db_alias).create(
                        name=full or (username or ''),
                        phone=(getattr(instance, 'usr_phn', None) or getattr(instance, 'phone', None) or None),
                    )
                    logger.info("[SALESPERSON CREATED (no-email)] for user %s on db=%s", getattr(instance, 'usr_name', None), db_alias)
                except Exception:
                    logger.exception("[SALESPERSON CREATE FAILED after IntegrityError] for user %s", getattr(instance, 'usr_name', None))
            except Exception:
                logger.exception("[SALESPERSON CREATE FAILED] for user %s", getattr(instance, 'usr_name', None))
    except Exception:
        logger.exception("Unexpected error while creating/updating SalesPerson for user %s", getattr(instance, 'usr_name', None))