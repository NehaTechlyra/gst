# import logging
# import threading
# from datetime import datetime, timedelta, timezone as dt_timezone
# from zoneinfo import ZoneInfo

# logger = logging.getLogger(__name__)
# IST_TZ = ZoneInfo("Asia/Kolkata")


# def send_trial_reminder_job():
#     from company.models import Company
#     from Lyraerp.utils.email_utils import send_trial_reminder_email

#     logger.info("[SCHEDULER] JOB 1 - Running trial reminder email check...")
#     sent = 0
#     skipped = 0
#     errors = 0

#     try:
#         companies = Company.objects.using('default').filter(
#             trial_active=True,
#             trial_started_at__isnull=False,
#             trial_reminder_sent=False,
#         )
#         for company in companies:
#             recipient = company.contact_email or company.email
#             if not recipient:
#                 skipped += 1
#                 continue
#             if company.should_send_trial_reminder():
#                 try:
#                     success = send_trial_reminder_email(company, recipient)
#                     if success:
#                         sent += 1
#                         logger.info(f"  [OK] Reminder sent -> {company.name} ({recipient})")
#                     else:
#                         errors += 1
#                 except Exception as e:
#                     errors += 1
#                     logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
#             else:
#                 skipped += 1
#     except Exception as e:
#         logger.error(f"[SCHEDULER] JOB 1 ERROR: {e}", exc_info=True)

#     logger.info(f"[SCHEDULER] JOB 1 DONE - {sent} sent, {skipped} skipped, {errors} errors")


# def send_trial_expired_job():
#     from company.models import Company
#     from Lyraerp.utils.email_utils import send_trial_expired_email

#     logger.info("[SCHEDULER] JOB 2 - Running trial expired email check...")
#     sent = 0
#     skipped = 0
#     errors = 0

#     try:
#         companies = Company.objects.using('default').filter(
#             trial_active=True,
#             trial_started_at__isnull=False,
#         )
#         for company in companies:
#             recipient = company.contact_email or company.email
#             if not recipient:
#                 skipped += 1
#                 continue
#             if company.should_send_trial_expired_email():
#                 try:
#                     success = send_trial_expired_email(company, recipient)
#                     if success:
#                         sent += 1
#                         logger.info(f"  [OK] Expired email sent -> {company.name} ({recipient})")
#                     else:
#                         errors += 1
#                 except Exception as e:
#                     errors += 1
#                     logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
#             else:
#                 skipped += 1
#     except Exception as e:
#         logger.error(f"[SCHEDULER] JOB 2 ERROR: {e}", exc_info=True)

#     logger.info(f"[SCHEDULER] JOB 2 DONE - {sent} sent, {skipped} skipped, {errors} errors")


# def send_trial_expired_on_day15_job():
#     from company.models import Company
#     from Lyraerp.utils.email_utils import send_trial_expired_email
#     from django.utils import timezone

#     logger.info("[SCHEDULER] JOB 3 - Running day-15 expired email check...")
#     sent = 0
#     skipped = 0
#     errors = 0

#     try:
#         # Send the first "trial expired" email on the day AFTER the
#         # trial_expires_at date (i.e. if expiry is 25th, send on 26th).
#         today = timezone.now().date()
#         yesterday = today - timedelta(days=1)
#         companies = Company.objects.using('default').filter(
#             trial_active=True,
#             trial_started_at__isnull=False,
#             trial_expires_at__date=yesterday,
#             trial_expired_email_last_sent__isnull=True,
#         )
#         for company in companies:
#             if company.has_valid_license():
#                 skipped += 1
#                 continue
#             recipient = company.contact_email or company.email
#             if not recipient:
#                 skipped += 1
#                 continue
#             try:
#                 success = send_trial_expired_email(company, recipient)
#                 if success:
#                     sent += 1
#                     logger.info(f"  [OK] Day-15 email sent -> {company.name} ({recipient})")
#                 else:
#                     errors += 1
#             except Exception as e:
#                 errors += 1
#                 logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
#     except Exception as e:
#         logger.error(f"[SCHEDULER] JOB 3 ERROR: {e}", exc_info=True)

#     logger.info(f"[SCHEDULER] JOB 3 DONE - {sent} sent, {skipped} skipped, {errors} errors")


# def mark_licenses_expired_job():
#     """
#     Mark licenses as expired by setting is_license_expired flag in ALL COMPANY DATABASES.
#     This runs first, before sending emails.
    
#     If expiry_date = Feb 25, this sets is_license_expired=True on Feb 26 at daily job time.
#     """
#     from company.models import Company
#     from company_settings.models import LicenseKey
#     from Lyraerp.utils.db_utils import register_database
#     from django.utils import timezone
#     from django.db import ProgrammingError

#     logger.info("[SCHEDULER] JOB 3.5 - Marking expired licenses in all company databases...")
#     marked = 0
#     skipped = 0
#     errors = 0

#     try:
#         today = timezone.now().date()
        
#         # Get all companies from master DB
#         companies = Company.objects.using('default').filter(db_created=True)
        
#         for company in companies:
#             try:
#                 company_db = company.db_name
#                 if not company_db:
#                     skipped += 1
#                     continue
                
#                 # Register the database connection first
#                 register_database(company_db)
                
#                 try:
#                     # Find licenses in THIS company's database where today > expiry_date
#                     licenses = LicenseKey.objects.using(company_db).filter(
#                         is_active=True,
#                         is_license_expired=False,
#                         expiry_date__lt=today  # expiry_date is in the past
#                     )
                    
#                     for lic in licenses:
#                         try:
#                             lic.is_license_expired = True
#                             lic.save(update_fields=['is_license_expired'])
#                             marked += 1
#                             logger.info(f"  [OK] Marked as expired [{company.name}] -> {lic.company.name} (expired: {lic.expiry_date})")
#                         except Exception as e:
#                             errors += 1
#                             logger.error(f"  [ERROR] [{company.name}] License {getattr(lic, 'id', '?')}: {e}", exc_info=True)
#                 except ProgrammingError as e:
#                     # Table doesn't exist yet in this company's DB
#                     logger.debug(f"[SCHEDULER] JOB 3.5 [{company.name}] - LicenseKey table doesn't exist: {e}")
#                     skipped += 1
                
#             except Exception as e:
#                 errors += 1
#                 logger.error(f"[SCHEDULER] JOB 3.5 ERROR processing company: {e}", exc_info=True)
                
#     except Exception as e:
#         logger.error(f"[SCHEDULER] JOB 3.5 ERROR: {e}", exc_info=True)

#     logger.info(f"[SCHEDULER] JOB 3.5 DONE - {marked} marked, {skipped} skipped, {errors} errors")


# def send_license_expired_job():
#     """
#     Send license expired emails from ALL COMPANY DATABASES.
#     """
#     from company.models import Company
#     from company_settings.models import LicenseKey
#     from Lyraerp.utils.email_utils import send_license_expired_email
#     from Lyraerp.utils.db_utils import register_database
#     from django.utils import timezone
#     from django.db import ProgrammingError

#     logger.info("[SCHEDULER] JOB 4 - Running license expired email check in all company databases...")
#     sent = 0
#     skipped = 0
#     errors = 0

#     try:
#         today = timezone.now().date()
#         yesterday = today - timedelta(days=1)

#         # Get all companies from master DB
#         companies = Company.objects.using('default').filter(db_created=True)
        
#         for company in companies:
#             try:
#                 company_db = company.db_name
#                 if not company_db:
#                     skipped += 1
#                     continue
                
#                 # Register the database connection first
#                 register_database(company_db)
                
#                 try:
#                     # Find licenses in THIS company's database where:
#                     # 1. is_license_expired flag is True (set by mark_licenses_expired_job)
#                     # 2. expiry_date == yesterday (just expired yesterday, now today is marked as expired)
#                     # 3. license_expired_email_last_sent is None (first time sending)
#                     licenses = LicenseKey.objects.using(company_db).filter(
#                         is_active=True,
#                         is_license_expired=True,
#                         expiry_date=yesterday,
#                         license_expired_email_last_sent__isnull=True,
#                     )
                    
#                     for lic in licenses:
#                         try:
#                             recipient = None
#                             try:
#                                 recipient = lic.company.contact_email or lic.company.email
#                             except Exception:
#                                 recipient = None
                            
#                             if not recipient:
#                                 skipped += 1
#                                 continue

#                             # Send first-time expiry email
#                             success = send_license_expired_email(lic, recipient)
#                             if success:
#                                 sent += 1
#                                 logger.info(f"  [OK] [{company.name}] License expired email sent -> {lic.company.name} ({recipient})")
#                             else:
#                                 errors += 1
#                         except Exception as e:
#                             errors += 1
#                             logger.error(f"  [ERROR] [{company.name}] License {getattr(lic, 'id', '?')}: {e}", exc_info=True)
#                 except ProgrammingError as e:
#                     # Table doesn't exist yet in this company's DB
#                     logger.debug(f"[SCHEDULER] JOB 4 [{company.name}] - LicenseKey table doesn't exist: {e}")
#                     skipped += 1
                    
#             except Exception as e:
#                 errors += 1
#                 logger.error(f"[SCHEDULER] JOB 4 ERROR processing company: {e}", exc_info=True)
#     except Exception as e:
#         logger.error(f"[SCHEDULER] JOB 4 ERROR: {e}", exc_info=True)

#     logger.info(f"[SCHEDULER] JOB 4 DONE - {sent} sent, {skipped} skipped, {errors} errors")


# def _run_all_jobs():
#     logger.info("[SCHEDULER] Running all jobs...")
#     send_trial_reminder_job()
#     send_trial_expired_on_day15_job()
#     send_trial_expired_job()
#     mark_licenses_expired_job()  # Mark licenses as expired (set is_license_expired flag)
#     send_license_expired_job()  # Send license expired emails
#     run_scheduled_backups_job()  # Run auto backup schedules updt by neha on 5-3-26
#     logger.info("[SCHEDULER] All jobs completed")


# def _seconds_until_utc(hour, minute):
#     """Calculate seconds until next occurrence of hour:minute in UTC."""
#     # Use UTC time explicitly — works correctly regardless of server timezone
#     now_utc = datetime.now(dt_timezone.utc)
#     target_utc = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)

#     if target_utc <= now_utc:
#         target_utc += timedelta(days=1)

#     diff = (target_utc - now_utc).total_seconds()
#     logger.info(
#         f"[SCHEDULER] Now (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')} | "
#         f"Next run (UTC): {target_utc.strftime('%Y-%m-%d %H:%M:%S')} | "
#         f"Seconds away: {diff:.0f}"
#     )
#     return diff


# def _job_runner(hour, minute):
#     try:
#         _run_all_jobs()
#     except Exception as e:
#         logger.error(f"[SCHEDULER] Job runner error: {e}", exc_info=True)
#     finally:
#         _schedule_next(hour, minute)


# def _schedule_next(hour, minute):
#     delay = _seconds_until_utc(hour, minute)
#     timer = threading.Timer(delay, _job_runner, args=[hour, minute])
#     timer.daemon = True
#     timer.start()
#     return timer

# def _is_backup_due(schedule, now_ist):
#     run_time = schedule.run_time
#     if now_ist.hour != run_time.hour or now_ist.minute != run_time.minute:
#         return False

#     if schedule.frequency == 'daily':
#         return True

#     if schedule.frequency == 'weekly':
#         return now_ist.strftime('%A').lower() == (schedule.weekday or '').lower()

#     if schedule.frequency == 'monthly':
#         return now_ist.day == (schedule.month_day or 1)

#     return False


# def run_scheduled_backups_job():
#     from django.utils import timezone
#     from django.db import ProgrammingError
#     from company.models import Company
#     from system_settings.models import BackupSchedule
#     from system_settings.backup_utils import create_database_backup
#     from Lyraerp.utils.db_utils import register_database

#     # Evaluate backup schedules in IST regardless of Django TIME_ZONE setting.
#     now_ist = timezone.now().astimezone(IST_TZ)
#     processed = 0
#     created = 0
#     skipped = 0
#     errors = 0

#     try:
#         companies = Company.objects.using('default').filter(db_created=True)
#         for company in companies:
#             try:
#                 db_name = company.db_name
#                 if not db_name:
#                     skipped += 1
#                     continue

#                 register_database(db_name)
#                 try:
#                     schedule = BackupSchedule.objects.using(db_name).first()
#                 except ProgrammingError:
#                     skipped += 1
#                     continue

#                 if not schedule or not schedule.is_enabled:
#                     skipped += 1
#                     continue

#                 if not _is_backup_due(schedule, now_ist):
#                     skipped += 1
#                     continue

#                 if schedule.last_run_at:
#                     last_ist = schedule.last_run_at.astimezone(IST_TZ)
#                     if (
#                         last_ist.date() == now_ist.date() and
#                         last_ist.hour == now_ist.hour and
#                         last_ist.minute == now_ist.minute
#                     ):
#                         skipped += 1
#                         continue

#                 backup_file = create_database_backup(
#                     db_alias=db_name,
#                     company_code=company.company_code or db_name
#                 )
#                 schedule.last_run_at = timezone.now()
#                 schedule.save(using=db_name, update_fields=['last_run_at', 'updated_at'])

#                 processed += 1
#                 created += 1
#                 logger.info(f"[SCHEDULER] [BACKUP] Created -> {company.name} ({backup_file.name})")
#             except Exception as e:
#                 errors += 1
#                 logger.error(f"[SCHEDULER] [BACKUP] Error for company {getattr(company, 'name', '?')}: {e}", exc_info=True)
#     except Exception as e:
#         errors += 1
#         logger.error(f"[SCHEDULER] [BACKUP] Job error: {e}", exc_info=True)

#     if processed or errors:
#         logger.info(f"[SCHEDULER] [BACKUP] DONE - {created} created, {skipped} skipped, {errors} errors")

# def _backup_poll_runner(interval_seconds):
#     try:
#         run_scheduled_backups_job()
#     except Exception as e:
#         logger.error(f"[SCHEDULER] Backup poller error: {e}", exc_info=True)
#     finally:
#         _schedule_backup_poll(interval_seconds)


# def _schedule_backup_poll(interval_seconds=60):
#     timer = threading.Timer(interval_seconds, _backup_poll_runner, args=[interval_seconds])
#     timer.daemon = True
#     timer.start()
#     return timer


# def start():
#     # Set your desired daily send time in UTC
#     # UTC 04:00 = IST 09:30 (good morning send time for India)
#     # UTC 10:00 = IST 15:30
#     # Adjust as needed for your production timezone
#     HOUR = 9
#     MINUTE = 36

#     _schedule_next(HOUR, MINUTE)
#     _schedule_backup_poll(60)
#     ist_total_minutes = (HOUR * 60 + MINUTE + 330) % (24 * 60)
#     ist_hour = ist_total_minutes // 60
#     ist_minute = ist_total_minutes % 60
#     logger.info(
#         f"[OK] [SCHEDULER] Scheduler started - "
#         f"daily at {HOUR:02d}:{MINUTE:02d} UTC "
#         # f"(IST: {(HOUR + 5) % 24:02d}:{(MINUTE + 30) % 70:02d})"
#         f"(IST: {ist_hour:02d}:{ist_minute:02d})"
#     )



import logging
import threading
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo
from django.db import connections

logger = logging.getLogger(__name__)
IST_TZ = ZoneInfo("Asia/Kolkata")


def _close_registered_connection(db_alias):
    """Close per-company connections opened by the scheduler."""
    if not db_alias or db_alias == 'default':
        return
    try:
        if db_alias in connections:
            connections[db_alias].close()
            logger.debug(f"[SCHEDULER] Closed connection for {db_alias}")
    except Exception as exc:
        logger.debug(f"[SCHEDULER] Failed to close connection {db_alias}: {exc}")


def _count_master_db_records(company_id):
    """
    Count related records in master database for a company.
    
    These records will be cascade-deleted when the Company is deleted.
    
    Args:
        company_id: ID of the Company
        
    Returns:
        Total count of related records
    """
    from django.db.models.deletion import CASCADE
    from company.models import Company
    
    total = 0
    using_db = 'default'
    
    for relation in Company._meta.related_objects:
        if relation.on_delete is not CASCADE:
            continue

        try:
            model = relation.related_model
            if not _master_table_exists(model):
                continue
            lookup = f"{relation.field.name}_id"
            count = model._base_manager.using(using_db).filter(**{lookup: company_id}).count()
            if count > 0:
                total += count
        except Exception as e:
            logger.warning(
                "[SCHEDULER] Error counting %s.%s: %s",
                relation.related_model._meta.app_label,
                relation.related_model.__name__,
                e,
            )
            continue
    
    return total


def _master_table_exists(model):
    """Return True if a related model's table exists in the master database."""
    try:
        return model._meta.db_table in connections['default'].introspection.table_names()
    except Exception as exc:
        logger.warning(
            "[SCHEDULER] Could not inspect master table %s: %s",
            model._meta.db_table,
            exc,
        )
        return False


def _delete_master_company_entry(company_id):
    """
    Delete a Company row from the master DB without querying tenant-only tables.

    Django's normal cascade collector follows every model relation to Company, even
    models whose tables only exist in tenant databases. In this project that can
    make master cleanup fail with "table does not exist" after a tenant DB is gone.
    """
    from django.db.models.deletion import CASCADE, SET_NULL
    from company.models import Company

    for relation in Company._meta.related_objects:
        model = relation.related_model
        if not _master_table_exists(model):
            continue

        lookup = f"{relation.field.name}_id"
        qs = model._base_manager.using('default').filter(**{lookup: company_id})

        if relation.on_delete is CASCADE:
            qs.delete()
        elif relation.on_delete is SET_NULL and relation.field.null:
            qs.update(**{relation.field.name: None})
        elif qs.exists():
            raise RuntimeError(
                f"Cannot delete Company {company_id}; protected relation exists: "
                f"{model._meta.label}.{relation.field.name}"
            )

    with connections['default'].cursor() as cursor:
        cursor.execute(
            f"DELETE FROM `{Company._meta.db_table}` WHERE `{Company._meta.pk.column}` = %s",
            [company_id],
        )
        return cursor.rowcount


def send_trial_reminder_job():
    from company.models import Company
    from Lyraerp.utils.email_utils import send_trial_reminder_email

    logger.info("[SCHEDULER] JOB 1 - Running trial reminder email check...")
    sent = 0
    skipped = 0
    errors = 0

    try:
        companies = Company.objects.using('default').filter(
            trial_active=True,
            trial_started_at__isnull=False,
            trial_reminder_sent=False,
        )
        for company in companies:
            recipient = company.contact_email or company.email
            if not recipient:
                skipped += 1
                continue
            if company.should_send_trial_reminder():
                try:
                    success = send_trial_reminder_email(company, recipient)
                    if success:
                        sent += 1
                        logger.info(f"  [OK] Reminder sent -> {company.name} ({recipient})")
                    else:
                        errors += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
            else:
                skipped += 1
    except Exception as e:
        logger.error(f"[SCHEDULER] JOB 1 ERROR: {e}", exc_info=True)

    logger.info(f"[SCHEDULER] JOB 1 DONE - {sent} sent, {skipped} skipped, {errors} errors")


def send_trial_expired_job():
    from company.models import Company
    from Lyraerp.utils.email_utils import send_trial_expired_email

    logger.info("[SCHEDULER] JOB 2 - Running trial expired email check...")
    sent = 0
    skipped = 0
    errors = 0

    try:
        companies = Company.objects.using('default').filter(
            trial_active=True,
            trial_started_at__isnull=False,
        )
        for company in companies:
            recipient = company.contact_email or company.email
            if not recipient:
                skipped += 1
                continue
            if company.should_send_trial_expired_email():
                try:
                    success = send_trial_expired_email(company, recipient)
                    if success:
                        sent += 1
                        logger.info(f"  [OK] Expired email sent -> {company.name} ({recipient})")
                    else:
                        errors += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
            else:
                skipped += 1
    except Exception as e:
        logger.error(f"[SCHEDULER] JOB 2 ERROR: {e}", exc_info=True)

    logger.info(f"[SCHEDULER] JOB 2 DONE - {sent} sent, {skipped} skipped, {errors} errors")


def send_trial_expired_on_day15_job():
    from company.models import Company
    from Lyraerp.utils.email_utils import send_trial_expired_email
    from django.utils import timezone

    logger.info("[SCHEDULER] JOB 3 - Running day-15 expired email check...")
    sent = 0
    skipped = 0
    errors = 0

    try:
        # Send the first "trial expired" email on the day AFTER the
        # trial_expires_at date (i.e. if expiry is 25th, send on 26th).
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        companies = Company.objects.using('default').filter(
            trial_active=True,
            trial_started_at__isnull=False,
            trial_expires_at__date=yesterday,
            trial_expired_email_last_sent__isnull=True,
        )
        for company in companies:
            if company.has_valid_license():
                skipped += 1
                continue
            recipient = company.contact_email or company.email
            if not recipient:
                skipped += 1
                continue
            try:
                success = send_trial_expired_email(company, recipient)
                if success:
                    sent += 1
                    logger.info(f"  [OK] Day-15 email sent -> {company.name} ({recipient})")
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"  [ERROR] {company.name}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[SCHEDULER] JOB 3 ERROR: {e}", exc_info=True)

    logger.info(f"[SCHEDULER] JOB 3 DONE - {sent} sent, {skipped} skipped, {errors} errors")


def mark_licenses_expired_job():
    """
    Mark licenses as expired by setting is_license_expired flag in ALL COMPANY DATABASES.
    This runs first, before sending emails.
    
    If expiry_date = Feb 25, this sets is_license_expired=True on Feb 26 at daily job time.
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import register_database
    from django.utils import timezone
    from django.db import ProgrammingError

    logger.info("[SCHEDULER] JOB 3.5 - Marking expired licenses in all company databases...")
    marked = 0
    skipped = 0
    errors = 0

    try:
        today = timezone.now().date()
        
        # Get all companies from master DB
        companies = Company.objects.using('default').filter(db_created=True)
        
        for company in companies:
            try:
                company_db = company.db_name
                if not company_db:
                    skipped += 1
                    continue

                # Register the database connection first
                register_database(company_db)

                try:
                    # Find licenses in THIS company's database where today > expiry_date
                    licenses = LicenseKey.objects.using(company_db).filter(
                        is_active=True,
                        is_license_expired=False,
                        expiry_date__lt=today  # expiry_date is in the past
                    )
                    
                    for lic in licenses:
                        try:
                            lic.is_license_expired = True
                            lic.save(update_fields=['is_license_expired'])
                            marked += 1
                            logger.info(f"  [OK] Marked as expired [{company.name}] -> {lic.company.name} (expired: {lic.expiry_date})")
                        except Exception as e:
                            errors += 1
                            logger.error(f"  [ERROR] [{company.name}] License {getattr(lic, 'id', '?')}: {e}", exc_info=True)
                except ProgrammingError as e:
                    # Table doesn't exist yet in this company's DB
                    logger.debug(f"[SCHEDULER] JOB 3.5 [{company.name}] - LicenseKey table doesn't exist: {e}")
                    skipped += 1
                finally:
                    _close_registered_connection(company_db)
            
            except Exception as e:
                errors += 1
                logger.error(f"[SCHEDULER] JOB 3.5 ERROR processing company: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"[SCHEDULER] JOB 3.5 ERROR: {e}", exc_info=True)

    logger.info(f"[SCHEDULER] JOB 3.5 DONE - {marked} marked, {skipped} skipped, {errors} errors")


def send_license_expired_job():
    """
    Send license expired emails from ALL COMPANY DATABASES.
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.email_utils import send_license_expired_email
    from Lyraerp.utils.db_utils import register_database
    from django.utils import timezone
    from django.db import ProgrammingError

    logger.info("[SCHEDULER] JOB 4 - Running license expired email check in all company databases...")
    sent = 0
    skipped = 0
    errors = 0

    try:
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Get all companies from master DB
        companies = Company.objects.using('default').filter(db_created=True)
        
        for company in companies:
            try:
                company_db = company.db_name
                if not company_db:
                    skipped += 1
                    continue
                
                # Register the database connection first
                register_database(company_db)
                
                try:
                    # Find licenses in THIS company's database where:
                    # 1. is_license_expired flag is True (set by mark_licenses_expired_job)
                    # 2. expiry_date == yesterday (just expired yesterday, now today is marked as expired)
                    # 3. license_expired_email_last_sent is None (first time sending)
                    licenses = LicenseKey.objects.using(company_db).filter(
                        is_active=True,
                        is_license_expired=True,
                        expiry_date=yesterday,
                        license_expired_email_last_sent__isnull=True,
                    )
                    
                    for lic in licenses:
                        try:
                            recipient = None
                            try:
                                recipient = lic.company.contact_email or lic.company.email
                            except Exception:
                                recipient = None
                            
                            if not recipient:
                                skipped += 1
                                continue

                            # Send first-time expiry email
                            success = send_license_expired_email(lic, recipient)
                            if success:
                                sent += 1
                                logger.info(f"  [OK] [{company.name}] License expired email sent -> {lic.company.name} ({recipient})")
                            else:
                                errors += 1
                        except Exception as e:
                            errors += 1
                            logger.error(f"  [ERROR] [{company.name}] License {getattr(lic, 'id', '?')}: {e}", exc_info=True)
                except ProgrammingError as e:
                    # Table doesn't exist yet in this company's DB
                    logger.debug(f"[SCHEDULER] JOB 4 [{company.name}] - LicenseKey table doesn't exist: {e}")
                    skipped += 1
                finally:
                    _close_registered_connection(company_db)
            
            except Exception as e:
                errors += 1
                logger.error(f"[SCHEDULER] JOB 4 ERROR processing company: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[SCHEDULER] JOB 4 ERROR: {e}", exc_info=True)

    logger.info(f"[SCHEDULER] JOB 4 DONE - {sent} sent, {skipped} skipped, {errors} errors")


def send_deletion_warning_emails_job():
    """Send deletion warning emails for expired databases in grace period."""
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.trial_utils import send_deletion_warning_email
    from Lyraerp.utils.db_utils import register_database
    from django.utils import timezone

    logger.info("[SCHEDULER] JOB 4.5 - Sending deletion warning emails...")
    sent = 0
    skipped = 0
    errors = 0
    now = timezone.now()

    companies = Company.objects.using('default').filter(
        db_created=True,
        db_name__isnull=False,
    )

    for company in companies:
        try:
            # Determine expiry date
            register_database(company.db_name)
            license_obj = LicenseKey.objects.using(company.db_name).filter(
                company_id=company.pk,
            ).first()

            if license_obj and license_obj.expiry_date:
                expiry_date = license_obj.expiry_date
            elif company.trial_expires_at:
                expiry_date = company.trial_expires_at.date() if hasattr(company.trial_expires_at, 'date') else company.trial_expires_at
            else:
                skipped += 1
                continue

            # Check if in grace period (0-7 days after expiry)
            if hasattr(expiry_date, 'date'):
                expiry_only = expiry_date.date()
            else:
                expiry_only = expiry_date
            
            days_past_expiry = (now.date() - expiry_only).days
            
            # Send warning only during 7-day grace period
            if days_past_expiry < 0 or days_past_expiry >= 7:
                skipped += 1
                _close_registered_connection(company.db_name)
                continue

            # Check if company has valid license
            has_valid_license = bool(
                license_obj
                and license_obj.is_active
                and not license_obj.is_license_expired
                and (license_obj.expiry_date is None or license_obj.expiry_date >= now.date())
            )
            if has_valid_license:
                skipped += 1
                _close_registered_connection(company.db_name)
                continue

            # Check if we should send warning (max 3 times, every 48 hours)
            if company.should_send_deletion_warning_email():
                if send_deletion_warning_email(company, expiry_date=expiry_only):
                    sent += 1
                else:
                    errors += 1
            else:
                skipped += 1

            _close_registered_connection(company.db_name)

        except Exception as exc:
            errors += 1
            logger.error(
                "[SCHEDULER] JOB 4.5 - Failed for '%s': %s",
                company.name,
                exc,
                exc_info=True,
            )
            _close_registered_connection(company.db_name)

    logger.info(
        "[SCHEDULER] JOB 4.5 DONE - %s sent, %s skipped, %s errors",
        sent,
        skipped,
        errors,
    )


def delete_expired_trial_databases_job(dry_run=False, remove_company_entry=True):
    """Delete tenant databases seven days after trial or license expiry.
    
    Args:
        dry_run (bool): If True, only log eligible companies without deletion
        remove_company_entry (bool): If True, completely delete Company entry from main DB
                                     If False, only mark as deleted (db_created=False, db_name=None)
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import (
        database_exists,
        delete_company_database,
        register_database,
    )
    from django.db.models import Q
    from django.utils import timezone

    logger.info("[SCHEDULER] JOB 5 - Checking expired trial and license databases (remove_company_entry=%s)...", remove_company_entry)
    deleted = 0
    skipped = 0
    errors = 0
    now = timezone.now()

    grace_cutoff = now - timedelta(days=7)
    companies = Company.objects.using('default').filter(
        Q(db_created=True, db_name__isnull=False)
        | Q(db_name__isnull=True, trial_expires_at__lte=grace_cutoff)
    )

    for company in companies:
        try:
            company_name = company.name
            company_db_name = company.db_name
            company_pk = company.pk
            tenant_db_exists = database_exists(company_db_name)
            license_obj = None
            
            if tenant_db_exists:
                register_database(company_db_name)
                license_obj = LicenseKey.objects.using(company_db_name).filter(
                    company_id=company.pk,
                ).first()
            else:
                logger.warning(
                    "[SCHEDULER] JOB 5 - Tenant database '%s' for '%s' is already missing; "
                    "cleaning stale master Company entry",
                    company_db_name,
                    company_name,
                )

            if license_obj and license_obj.expiry_date:
                expiry_date = license_obj.expiry_date
                expiry_type = 'license'
            elif company.trial_expires_at:
                expiry_date = company.trial_expires_at.date() if company.trial_expires_at else None
                expiry_type = 'trial'
            elif not tenant_db_exists:
                expiry_date = now.date() - timedelta(days=7)
                expiry_type = 'missing database'
            else:
                expiry_date = None
                expiry_type = 'trial'

            if not expiry_date or now.date() < expiry_date + timedelta(days=7):
                skipped += 1
                continue

            has_valid_license = bool(
                license_obj
                and license_obj.is_active
                and not license_obj.is_license_expired
                and expiry_date >= now.date()
            )
            if has_valid_license:
                skipped += 1
                continue

            if dry_run:
                deleted += 1
                logger.info(
                    "[SCHEDULER] JOB 5 - Eligible (%s) '%s' (%s)",
                    expiry_type,
                    company_name,
                    company_db_name,
                )
                continue

            # Delete the company database. DROP IF EXISTS also keeps retry cleanup safe.
            if tenant_db_exists:
                _close_registered_connection(company_db_name)
                delete_company_database(company_db_name)
            
            # Remove or mark Company entry in main database
            if remove_company_entry:
                # ✓ COMPLETELY DELETE the Company entry from main database
                # This cascade-deletes all related records (bank accounts, licenses, settings, etc.)
                try:
                    from django.db import transaction
                    with transaction.atomic(using='default'):
                        # Count related records before deletion
                        related_count = _count_master_db_records(company_pk)
                        
                        deleted_rows = _delete_master_company_entry(company_pk)
                        
                        if deleted_rows:
                            deleted += 1
                            logger.warning(
                                "[SCHEDULER] JOB 5 - Completely removed: company '%s' (%s) "
                                "and %d related master database records after %s expiry",
                                company_name,
                                company_db_name,
                                related_count,
                                expiry_type,
                            )
                        else:
                            skipped += 1
                            logger.warning(
                                "[SCHEDULER] JOB 5 - Company '%s' (%s) was already absent from master DB",
                                company_name,
                                company_db_name,
                            )
                except Exception as delete_exc:
                    errors += 1
                    logger.error(
                        "[SCHEDULER] JOB 5 - Failed to remove Company entry for '%s': %s",
                        company_name,
                        delete_exc,
                        exc_info=True,
                    )
            else:
                # ✗ KEEP Company entry but mark as deleted
                try:
                    from django.db import transaction
                    with transaction.atomic(using='default'):
                        # Count related records
                        related_count = _count_master_db_records(company_pk)
                        
                        Company.objects.using('default').filter(pk=company_pk).update(
                            db_created=False,
                            db_name=None,
                        )
                        deleted += 1
                        logger.warning(
                            "[SCHEDULER] JOB 5 - Deleted %s database '%s' for '%s' "
                            "(Company entry archived with %d related records)",
                            expiry_type,
                            company_db_name,
                            company_name,
                            related_count,
                        )
                except Exception as update_exc:
                    errors += 1
                    logger.error(
                        "[SCHEDULER] JOB 5 - Failed to update Company entry for '%s': %s",
                        company_name,
                        update_exc,
                        exc_info=True,
                    )
        except Exception as exc:
            errors += 1
            logger.error(
                "[SCHEDULER] JOB 5 - Failed for '%s': %s",
                company.name,
                exc,
                exc_info=True,
            )
        finally:
            _close_registered_connection(company.db_name)

    logger.info(
        "[SCHEDULER] JOB 5 DONE - %s deleted, %s skipped, %s errors",
        deleted,
        skipped,
        errors,
    )
    return {'deleted': deleted, 'skipped': skipped, 'errors': errors}


def _run_all_jobs():
    logger.info("[SCHEDULER] Running all jobs...")
    send_trial_reminder_job()
    send_trial_expired_on_day15_job()
    send_trial_expired_job()
    mark_licenses_expired_job()  # Mark licenses as expired (set is_license_expired flag)
    send_license_expired_job()  # Send license expired emails
    send_deletion_warning_emails_job()  # Send deletion warning emails (3 times in 7-day grace period)
    delete_expired_trial_databases_job()  # Delete expired databases after 7-day grace
    run_scheduled_backups_job()  # Run auto backup schedules updt by neha on 5-3-26
    logger.info("[SCHEDULER] All jobs completed")


def _seconds_until_utc(hour, minute):
    """Calculate seconds until next occurrence of hour:minute in UTC."""
    # Use UTC time explicitly — works correctly regardless of server timezone
    now_utc = datetime.now(dt_timezone.utc)
    target_utc = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target_utc <= now_utc:
        target_utc += timedelta(days=1)

    diff = (target_utc - now_utc).total_seconds()
    logger.info(
        f"[SCHEDULER] Now (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Next run (UTC): {target_utc.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Seconds away: {diff:.0f}"
    )
    return diff


def _job_runner(hour, minute):
    try:
        _run_all_jobs()
    except Exception as e:
        logger.error(f"[SCHEDULER] Job runner error: {e}", exc_info=True)
    finally:
        _schedule_next(hour, minute)


def _schedule_next(hour, minute):
    delay = _seconds_until_utc(hour, minute)
    timer = threading.Timer(delay, _job_runner, args=[hour, minute])
    timer.daemon = True
    timer.start()
    return timer

def _is_backup_due(schedule, now_ist):
    run_time = schedule.run_time
    if now_ist.hour != run_time.hour or now_ist.minute != run_time.minute:
        return False

    if schedule.frequency == 'daily':
        return True

    if schedule.frequency == 'weekly':
        return now_ist.strftime('%A').lower() == (schedule.weekday or '').lower()

    if schedule.frequency == 'monthly':
        return now_ist.day == (schedule.month_day or 1)

    return False


def run_scheduled_backups_job():
    from django.utils import timezone
    from django.db import ProgrammingError
    from company.models import Company
    from system_settings.models import BackupSchedule
    from system_settings.backup_utils import create_database_backup
    from Lyraerp.utils.db_utils import register_database

    # Evaluate backup schedules in IST regardless of Django TIME_ZONE setting.
    now_ist = timezone.now().astimezone(IST_TZ)
    processed = 0
    created = 0
    skipped = 0
    errors = 0

    try:
        companies = Company.objects.using('default').filter(db_created=True)
        for company in companies:
            try:
                db_name = company.db_name
                if not db_name:
                    skipped += 1
                    continue

                register_database(db_name)
                try:
                    try:
                        schedule = BackupSchedule.objects.using(db_name).first()
                    except ProgrammingError:
                        skipped += 1
                        continue

                    if not schedule or not schedule.is_enabled:
                        skipped += 1
                        continue

                    if not _is_backup_due(schedule, now_ist):
                        skipped += 1
                        continue

                    if schedule.last_run_at:
                        last_ist = schedule.last_run_at.astimezone(IST_TZ)
                        if (
                            last_ist.date() == now_ist.date() and
                            last_ist.hour == now_ist.hour and
                            last_ist.minute == now_ist.minute
                        ):
                            skipped += 1
                            continue

                    backup_file = create_database_backup(
                        db_alias=db_name,
                        company_code=company.company_code or db_name
                    )
                    schedule.last_run_at = timezone.now()
                    schedule.save(using=db_name, update_fields=['last_run_at', 'updated_at'])

                    processed += 1
                    created += 1
                    logger.info(f"[SCHEDULER] [BACKUP] Created -> {company.name} ({backup_file.name})")
                finally:
                    _close_registered_connection(db_name)
            except Exception as e:
                errors += 1
                logger.error(f"[SCHEDULER] [BACKUP] Error for company {getattr(company, 'name', '?')}: {e}", exc_info=True)
    except Exception as e:
        errors += 1
        logger.error(f"[SCHEDULER] [BACKUP] Job error: {e}", exc_info=True)

    if processed or errors:
        logger.info(f"[SCHEDULER] [BACKUP] DONE - {created} created, {skipped} skipped, {errors} errors")

def _backup_poll_runner(interval_seconds):
    try:
        run_scheduled_backups_job()
    except Exception as e:
        logger.error(f"[SCHEDULER] Backup poller error: {e}", exc_info=True)
    finally:
        _schedule_backup_poll(interval_seconds)


def _schedule_backup_poll(interval_seconds=60):
    timer = threading.Timer(interval_seconds, _backup_poll_runner, args=[interval_seconds])
    timer.daemon = True
    timer.start()
    return timer


def start():
    # Set your desired daily send time in UTC
    # UTC 04:00 = IST 09:30 (good morning send time for India)
    # UTC 06:30 = IST 12:00
    # Adjust as needed for your production timezone
    HOUR = 6
    MINUTE = 45

    _schedule_next(HOUR, MINUTE)
    _schedule_backup_poll(60)
    ist_total_minutes = (HOUR * 60 + MINUTE + 330) % (24 * 60)
    ist_hour = ist_total_minutes // 60
    ist_minute = ist_total_minutes % 60
    logger.info(
        f"[OK] [SCHEDULER] Scheduler started - "
        f"daily at {HOUR:02d}:{MINUTE:02d} UTC "
        # f"(IST: {(HOUR + 5) % 24:02d}:{(MINUTE + 30) % 70:02d})"
        f"(IST: {ist_hour:02d}:{ist_minute:02d})"
    )
