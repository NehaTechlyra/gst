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


def _run_all_jobs():
    logger.info("[SCHEDULER] Running all jobs...")
    send_trial_reminder_job()
    send_trial_expired_on_day15_job()
    send_trial_expired_job()
    mark_licenses_expired_job()  # Mark licenses as expired (set is_license_expired flag)
    send_license_expired_job()  # Send license expired emails
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
    # UTC 10:00 = IST 15:30
    # Adjust as needed for your production timezone
    HOUR = 9
    MINUTE = 36

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
