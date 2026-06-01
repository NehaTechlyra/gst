"""
Async database migrations to speed up company signup
Runs data migrations in background thread
"""

import threading
import logging
import time
from django.core.management import call_command
from django.conf import settings
from django.db import transaction, connections
from django.utils import timezone

logger = logging.getLogger(__name__)

# Store background task status
MIGRATION_STATUS = {}

# Critical apps that must complete before using the database
CRITICAL_APPS = ['contenttypes', 'auth', 'company', 'user', 'currencies']


def run_critical_migrations(db_name):
    """
    Run ONLY critical migrations synchronously (blocking)
    These must complete before the database can be used
    """
    try:
        logger.info(f"[CRITICAL MIGRATE] Starting critical migrations for {db_name}")
        
        for app in CRITICAL_APPS:
            try:
                call_command(
                    'migrate',
                    app,
                    database=db_name,
                    interactive=False,
                    verbosity=0,
                    run_syncdb=False,
                    # fake_initial=True,
                )
                logger.info(f"[CRITICAL MIGRATE] ✅ {app} completed on {db_name}")
            except Exception as e:
                logger.warning(f"[CRITICAL MIGRATE] ⚠️ {app} failed: {e}")
                # Continue with other apps even if one fails
        
        logger.info(f"[CRITICAL MIGRATE] ✅ All critical migrations completed for {db_name}")
        return True
        
    except Exception as e:
        logger.error(f"[CRITICAL MIGRATE] ❌ Error during critical migrations: {e}", exc_info=True)
        return False


def run_migrations_async(db_name):
    """
    Run all remaining migrations asynchronously in background thread
    CRITICAL apps are already handled synchronously
    Updates MIGRATION_STATUS dict with progress
    """
    def _migrate():
        try:
            # close any existing connection in this thread – Django reuses connections per-thread
            if db_name in connections:
                connections[db_name].close()

            MIGRATION_STATUS[db_name] = {
                'status': 'running',
                'progress': 'Starting background migrations...',
                'error': None,
                'stage': 'migrations'
            }
            logger.info(f"[ASYNC MIGRATE] Starting background migrations for {db_name}")

            # create a small writer to push live progress back into status dict
            class _ProgressWriter:
                def write(self, data):
                    for line in data.splitlines():
                        if line.startswith('Applying '):
                            MIGRATION_STATUS[db_name]['progress'] = line
                    logger.debug(f"[MIGRATE OUTPUT] {data}")
                def flush(self):
                    pass

            # Run ALL migrations (includes re-running critical ones, which is safe)
            call_command(
                'migrate',
                database=db_name,
                interactive=False,
                verbosity=1,
                run_syncdb=False,
                fake_initial=True,
                stdout=_ProgressWriter(),
                stderr=_ProgressWriter(),
            )

            MIGRATION_STATUS[db_name] = {
                'status': 'completed',
                'progress': 'All migrations completed',
                'error': None,
                'stage': 'migrations'
            }
            logger.info(f"[ASYNC MIGRATE] ✅ Completed for {db_name}")

            # If the HSN import migration ran during this pass we may have
            # printed some progress messages to stdout earlier; for convenience
            # log a simple row count once everything has finished.  This makes
            # it easier to scan the log for the final state of the DB.
            try:
                from Items.models import HSNCode
                total = HSNCode.objects.using(db_name).count()
                logger.info(
                    f"[ASYNC MIGRATE] HSN codes present in {db_name}: {total:,}"
                )
            except Exception:
                pass

        except Exception as e:
            error_msg = str(e)
            MIGRATION_STATUS[db_name] = {
                'status': 'failed',
                'progress': 'Migration failed',
                'error': error_msg,
                'stage': 'migrations'
            }
            logger.error(f"[ASYNC MIGRATE] ❌ Failed for {db_name}: {error_msg}", exc_info=True)
    
    # Start background thread
    thread = threading.Thread(target=_migrate, daemon=True)
    thread.start()
    logger.info(f"[ASYNC MIGRATE] Background thread started for {db_name}")


def run_company_setup_async(db_name, company, role, custom_user, user):
    """
    Run complete company setup asynchronously (after critical migrations)
    Includes: full migrations, permissions, modules, data sync
    """
    def _setup():
        try:
            if db_name in connections:
                connections[db_name].close()

            MIGRATION_STATUS[db_name] = {
                'status': 'running',
                'progress': '1/7: Running remaining migrations...',
                'error': None,
                'stage': 'setup'
            }
            
            # STEP 4: Run all migrations
            logger.info(f"[SETUP ASYNC] Step 1/7: Running all migrations for {db_name}")

            # Instead of a single `call_command('migrate')` which leaves the user
            # staring at "Running remaining migrations..." for minutes, we
            # capture the output and push every "Applying ..." line back into
            # MIGRATION_STATUS so the front‑end can show which app is currently
            # being migrated.  This also makes the overall process feel faster.
            class _ProgressWriter:
                def write(self, data):
                    # split on newlines to handle incremental writes
                    for line in data.splitlines():
                        if line.startswith('Applying '):
                            # Example: "Applying sales.0001_initial..."
                            MIGRATION_STATUS[db_name]['progress'] = line
                    # also log whatever we receive for debugging
                    logger.debug(f"[MIGRATE OUTPUT] {data}")

                def flush(self):
                    pass

            call_command(
                'migrate',
                database=db_name,
                interactive=False,
                verbosity=1,
                run_syncdb=False,
                fake_initial=True,
                stdout=_ProgressWriter(),
                stderr=_ProgressWriter(),
            )
            
            # Import here to avoid circular imports
            from Lyraerp.utils.db_utils import (
                populate_permission_types,
                populate_modules_from_license,
                create_admin_role_permissions,
                sync_auth_user,
            )
            
            # STEP 5: Populate permissions
            MIGRATION_STATUS[db_name]['progress'] = '2/7: Setting up permissions...'
            logger.info(f"[SETUP ASYNC] Step 2/7: Populating permissions for {db_name}")
            populate_permission_types(db_name)
            
            # STEP 6: Populate modules
            MIGRATION_STATUS[db_name]['progress'] = '3/7: Configuring modules...'
            logger.info(f"[SETUP ASYNC] Step 3/7: Populating modules for {db_name}")
            populate_modules_from_license(db_name, None)
            
            # STEP 7: Sync company
            MIGRATION_STATUS[db_name]['progress'] = '4/7: Syncing company data...'
            logger.info(f"[SETUP ASYNC] Step 4/7: Syncing company to {db_name}")
            with transaction.atomic(using=db_name):
                from company.models import Company as CompanyModel
                # Reload fresh from master DB — the passed-in instance was
                # captured at signup time and may be missing fields like
                # tax_type that were saved later during registration steps.
                fresh_company = CompanyModel.objects.using('default').get(pk=company.id)
 
                skip_fields = {
                    'id', 'created_at', 'updated_at', 'created_by_id', 'updated_by_id'
                }
                field_values = {}
                for f in fresh_company._meta.fields:
                    if f.attname in skip_fields or f.name in skip_fields:
                        continue
                    field_values[f.attname] = getattr(fresh_company, f.attname)
 
                # Override setup-specific fields for the new company DB
                field_values['setup_complete'] = False
                field_values['db_created'] = True
                # ← ADD HERE: Don't overwrite setup_complete if registration
                # already finished before this async thread reached Step 4
                if fresh_company.setup_complete:
                    field_values['setup_complete'] = True
                else:
                    field_values['setup_complete'] = False
 
                CompanyModel.objects.using(db_name).update_or_create(
                    id=fresh_company.id,
                    defaults=field_values
                )
                logger.info(
                    f"[SETUP ASYNC] Company synced to {db_name} "
                    f"tax_type='{fresh_company.tax_type}' ✅"
                )
            
            # STEP 8: Create admin role
            MIGRATION_STATUS[db_name]['progress'] = '5/7: Creating admin role...'
            logger.info(f"[SETUP ASYNC] Step 5/7: Creating admin role in {db_name}")
            with transaction.atomic(using=db_name):
                from user.models import Role
                company_role = Role.objects.using(db_name).create(
                    id=role.id,
                    role_name="Admin",
                    description="Administrator role with full access",
                    company_id=company.id
                )
            
            # STEP 9: Create role permissions
            MIGRATION_STATUS[db_name]['progress'] = '6/7: Setting up role permissions...'
            logger.info(f"[SETUP ASYNC] Step 6/7: Creating role permissions in {db_name}")
            create_admin_role_permissions(db_name, company_role.id)
            
            # STEP 10: Create custom user
            logger.info(f"[SETUP ASYNC] Step 6b/7: Creating custom user in {db_name}")
            with transaction.atomic(using=db_name):
                from user.models import User as CustomUserModel
                CustomUserModel.objects.using(db_name).create(
                    usr_name=custom_user.usr_name,
                    usr_fname=custom_user.usr_fname,
                    usr_mail=custom_user.usr_mail,
                    usr_phn=custom_user.usr_phn,
                    usr_pwd=custom_user.usr_pwd,
                    usr_roleid=company_role,
                    crtd_at=timezone.now()
                )
            
            # STEP 11: Sync auth user
            MIGRATION_STATUS[db_name]['progress'] = '7/7: Finalizing setup...'
            logger.info(f"[SETUP ASYNC] Step 7/7: Syncing auth_user to {db_name}")
            sync_auth_user(user, db_name)
            
            # Mark entire setup as complete.  Note that "migrations" have
            # finished far earlier – the remaining steps above (permissions,
            # modules, sync, etc.) may have produced many logs.  This final
            # status update and log entry serve as the canonical closing
            # message for the database.
            MIGRATION_STATUS[db_name] = {
                'status': 'completed',
                'progress': 'Setup completed successfully',
                'error': None,
                'stage': 'setup',
                'completed_at': time.time()
            }
            logger.info(f"[SETUP ASYNC] ✅ Complete for {db_name}")

            # additional helpful information: report how many HSN codes ended up
            # in the new database (used to be printed earlier by the migration
            # file).  Including it here guarantees the summary appears after all
            # other setup logs.
            try:
                from Items.models import HSNCode
                total = HSNCode.objects.using(db_name).count()
                logger.info(
                    f"[SETUP ASYNC] HSN codes in {db_name}: {total:,} (created/skipped/error counts not available)"
                )
            except Exception:
                # quiet if the model/table doesn't yet exist or import fails
                pass
        except Exception as e:
            error_msg = str(e)
            MIGRATION_STATUS[db_name] = {
                'status': 'failed',
                'progress': 'Setup failed',
                'error': error_msg,
                'stage': 'setup'
            }
            logger.error(f"[SETUP ASYNC] ❌ Failed for {db_name}: {error_msg}", exc_info=True)
    
    # Start background thread
    thread = threading.Thread(target=_setup, daemon=True)
    thread.start()
    logger.info(f"[SETUP ASYNC] Background setup thread started for {db_name}")


def get_migration_status(db_name):
    """Get current migration status for database"""
    return MIGRATION_STATUS.get(db_name, {
        'status': 'pending',
        'progress': 'Queued for migration',
        'error': None,
        'stage': 'setup'
    })
