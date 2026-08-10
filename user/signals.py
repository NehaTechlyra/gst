import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model

from django.db import IntegrityError
from django.db.models.signals import post_save
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
    if not created:
        return

    # from crm.models import SalesPerson

    logger.info(f"[SIGNAL FIRED] Creating SalesPerson for user {instance.usr_name}")

    try:
        sp = SalesPerson.objects.using(instance._state.db or 'default').create(
            name=instance.usr_fname or instance.usr_name,
            email=instance.usr_mail,
            phone=instance.usr_phn,
        )
        logger.info(f"[SALESPERSON CREATED] id={sp.pk} on db={instance._state.db}")
    except Exception as e:
        logger.exception(f"[SALESPERSON CREATE FAILED] for user {instance.usr_name}: {e}")