import re
import logging
import secrets
from django.db import connections
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_db_name(company_name, company_id, company_code=None):
    """
    Generate a tenant database name that is unique across master databases.

    The database name now uses the generated company code as the main identifier,
    e.g. lyraerp_abc2026k7m2.
    """
    master_name = settings.DATABASES.get("default", {}).get("NAME", "master")
    clean_master = re.sub(r"[^a-z0-9]", "", str(master_name).lower()) or "master"

    if company_code:
        clean_name = re.sub(r"[^a-z0-9]+", "", str(company_code).lower()) or "company"
    else:
        clean_name = re.sub(r"[^a-z0-9]", "", company_name.lower()) or "company"

    # MySQL database names are limited to 64 characters.
    clean_master = clean_master[:16]
    clean_name = clean_name[:24]
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"

    base_name = f"lyraerp_{clean_name}"
    candidates = [base_name, f"{base_name}_{company_id}"]

    for candidate in candidates:
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                [candidate],
            )
            if not cursor.fetchone():
                return candidate

    for _ in range(50):
        suffix = "".join(secrets.choice(alphabet) for _ in range(6))
        db_name = f"{base_name}_{suffix}"

        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                [db_name],
            )
            if not cursor.fetchone():
                return db_name

    fallback = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"{base_name[:50]}_{fallback}"

def create_physical_database(db_name):
    """Create physical MySQL database"""
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                [db_name]
            )
            if cursor.fetchone():
                error_msg = (
                    f"Database {db_name} already exists. Refusing to reuse an "
                    "existing tenant database for a new company."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            cursor.execute(
                f"CREATE DATABASE `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            logger.info(f"[OK] Created physical database: {db_name}")
            return True

    except Exception as e:
        logger.error(f"[ERROR] Failed to create database {db_name}: {e}")
        raise

def register_database(db_name):
    """Register company database in Django settings"""
    if db_name in connections.databases:
        logger.debug(f"Database {db_name} already registered")
        return

    default_db = settings.DATABASES['default']

    connections.databases[db_name] = {
        'ENGINE': default_db['ENGINE'],
        'NAME': db_name,
        'USER': default_db['USER'],
        'PASSWORD': default_db['PASSWORD'],
        'HOST': default_db['HOST'],
        'PORT': default_db['PORT'],
        'ATOMIC_REQUESTS': default_db.get('ATOMIC_REQUESTS', False),
        'TIME_ZONE': default_db.get('TIME_ZONE', None),
        'CONN_HEALTH_CHECKS': default_db.get('CONN_HEALTH_CHECKS', False),
        'AUTOCOMMIT': default_db.get('AUTOCOMMIT', True),
        'CONN_MAX_AGE': default_db.get('CONN_MAX_AGE', 0),
        'OPTIONS': default_db.get('OPTIONS', {
            'init_command': "SET sql_mode=''",
            'charset': 'utf8mb4',
        }),
    }

    logger.info(f"[OK] Registered database: {db_name}")


def migrate_company_database(db_name):
    """
    Run migrations on company database.
    Migrates ONLY dual apps and ERP apps.
    """
    try:
        # Register database
        register_database(db_name)

        logger.info(f"[MIGRATING] Starting migrations for {db_name}...")

        # Test connection first
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT 1")
            logger.info(f"[OK] Database connection successful: {db_name}")
        except Exception as conn_error:
            logger.error(f"[ERROR] Database connection failed: {conn_error}")
            raise

        logger.info(f"[MIGRATING] Running migrations on {db_name}...")

        call_command(
            'migrate',
            database=db_name,
            verbosity=2,
            interactive=False,
            run_syncdb=False,
        )

        logger.info(f"[OK] All migrations completed for {db_name}")
        return True

    except Exception as e:
        logger.error(f"[ERROR] Migration failed for {db_name}: {e}", exc_info=True)
        raise


def sync_company_record(company):
    """
    Sync the full Company record from master DB → company DB.

    This should be called ONCE after migrate_company_database() completes
    during signup. It copies all non-relational fields from master to the
    company DB so that:
      - Trial fields are present in company DB from day one
      - Contact person details are present in company DB
      - All other company profile data is in sync

    Args:
        company: Company model instance (loaded from master DB)

    Returns:
        True on success, raises on failure
    """
    from company.models import Company
    from currencies.services import base_currency_code_from_country, ensure_base_currency_row

    if not company.db_name or not company.db_created:
        logger.warning(
            f"[SYNC] Cannot sync Company '{company.name}' — "
            f"db_name={company.db_name}, db_created={company.db_created}"
        )
        return False

    try:
        register_database(company.db_name)
        base_currency = (getattr(company, "base_currency", None) or "").strip().upper()[:3]
        if not base_currency:
            base_currency = base_currency_code_from_country(getattr(company, "country", None))
        if base_currency and getattr(company, "base_currency", None) != base_currency:
            Company.objects.using("default").filter(pk=company.pk).update(base_currency=base_currency)
            company.base_currency = base_currency

        # Fields to exclude from sync (auto-managed or FK references)
        skip_fields = {
            'id',
            'created_at',
            'updated_at',
            'created_by_id',
            'updated_by_id',
        }

        field_values = {}
        for f in company._meta.fields:
            if f.attname in skip_fields:
                continue
            if f.name in skip_fields:
                continue
            field_values[f.attname] = getattr(company, f.attname)

        Company.objects.using(company.db_name).update_or_create(
            id=company.pk,
            defaults=field_values
        )
        company_local = Company.objects.using(company.db_name).get(pk=company.pk)
        ensure_base_currency_row(company_local, company.db_name, getattr(company, "base_currency", None))

        logger.info(
            f"[SYNC] Successfully synced Company record to {company.db_name} "
            f"for '{company.name}' (pk={company.pk})"
        )
        return True

    except Exception as e:
        logger.error(
            f"[SYNC] Failed to sync Company record to {company.db_name} "
            f"for '{company.name}': {e}",
            exc_info=True
        )
        raise


def sync_trial_fields_master_to_company(company):
    """
    Sync only trial-related fields from master DB → company DB.

    Use this for targeted syncing after trial state changes, or as a
    repair utility for existing companies with missing trial data in
    their company DB.

    Args:
        company: Company instance (loaded from master DB, trial fields populated)

    Returns:
        True on success, False on failure
    """
    from company.models import Company

    if not company.db_name or not company.db_created:
        logger.warning(
            f"[SYNC] Cannot sync trial fields for '{company.name}' — DB not ready"
        )
        return False

    trial_fields = {
        'trial_active': company.trial_active,
        'trial_created_at': company.trial_created_at,
        'trial_started_at': company.trial_started_at,
        'trial_expires_at': company.trial_expires_at,
        'trial_reminder_sent': company.trial_reminder_sent,
        'trial_reminder_sent_at': company.trial_reminder_sent_at,
        'trial_expired_email_last_sent': company.trial_expired_email_last_sent,
        'is_trial_expired': company.is_trial_expired,
    }

    try:
        register_database(company.db_name)

        updated = Company.objects.using(company.db_name).filter(
            pk=company.pk
        ).update(**trial_fields)

        if updated == 0:
            logger.warning(
                f"[SYNC] Company pk={company.pk} not found in {company.db_name}. "
                f"Running full sync instead."
            )
            sync_company_record(company)
        else:
            logger.info(
                f"[SYNC] Trial fields synced to {company.db_name} for '{company.name}'"
            )

        return True

    except Exception as e:
        logger.error(
            f"[SYNC] Failed to sync trial fields for '{company.name}': {e}",
            exc_info=True
        )
        return False


def sync_contact_person_both_ways(company):
    """
    Ensure contact person fields are consistent across both DBs.

    Master DB is treated as the source of truth. If master has empty
    contact fields but company DB has them populated, this copies from
    company DB → master.

    If master has contact fields populated, it syncs master → company DB.

    Args:
        company: Company instance

    Returns:
        True on success
    """
    from company.models import Company

    if not company.db_name or not company.db_created:
        return False

    try:
        register_database(company.db_name)

        master = Company.objects.using('default').get(pk=company.pk)
        company_record = Company.objects.using(company.db_name).filter(
            pk=company.pk
        ).first()

        if not company_record:
            logger.warning(
                f"[SYNC] Company record not found in {company.db_name}, running full sync"
            )
            sync_company_record(master)
            return True

        contact_fields = ['contact_person', 'contact_email', 'contact_phone']

        # Determine direction: if master is empty but company DB has data,
        # sync company DB → master
        master_has_contact = any(
            getattr(master, f) for f in contact_fields
        )
        company_has_contact = any(
            getattr(company_record, f) for f in contact_fields
        )

        if not master_has_contact and company_has_contact:
            # Company DB → master
            Company.objects.using('default').filter(pk=company.pk).update(
                contact_person=company_record.contact_person,
                contact_email=company_record.contact_email,
                contact_phone=company_record.contact_phone,
            )
            logger.info(
                f"[SYNC] Copied contact person from company DB → master for '{master.name}'"
            )

        elif master_has_contact:
            # Master → company DB
            Company.objects.using(company.db_name).filter(pk=company.pk).update(
                contact_person=master.contact_person,
                contact_email=master.contact_email,
                contact_phone=master.contact_phone,
            )
            logger.info(
                f"[SYNC] Copied contact person from master → company DB for '{master.name}'"
            )

        return True

    except Exception as e:
        logger.error(
            f"[SYNC] Failed to sync contact person for company pk={company.pk}: {e}",
            exc_info=True
        )
        return False


def repair_company_db_sync(company_pk):
    """
    Full repair utility: syncs all Company fields from master → company DB,
    then ensures contact person is consistent.

    Use this as a management command or shell one-liner to fix existing
    companies with missing data in their company DB.

    Args:
        company_pk: Primary key of the Company in master DB

    Usage in Django shell:
        from Lyraerp.utils.db_utils import repair_company_db_sync
        repair_company_db_sync(1)
    """
    from company.models import Company

    try:
        company = Company.objects.using('default').get(pk=company_pk)
        logger.info(f"[REPAIR] Starting repair for '{company.name}' (pk={company_pk})")

        # Step 1: Full sync from master → company DB
        sync_company_record(company)

        # Step 2: Fix contact person direction
        sync_contact_person_both_ways(company)

        logger.info(f"[REPAIR] Repair complete for '{company.name}'")
        return True

    except Exception as e:
        logger.error(f"[REPAIR] Failed to repair company pk={company_pk}: {e}", exc_info=True)
        return False


def delete_company_database(db_name):
    """Delete physical database"""
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
        logger.info(f"[OK] Deleted database: {db_name}")

        if db_name in connections.databases:
            del connections.databases[db_name]

    except Exception as e:
        logger.error(f"[ERROR] Failed to delete database {db_name}: {e}")
        raise


def test_database_connection(db_name):
    """Test database connection"""
    try:
        register_database(db_name)
        connection = connections[db_name]
        connection.ensure_connection()
        logger.info(f"[OK] Connection test passed: {db_name}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Connection test failed for {db_name}: {e}")
        return False


def sync_auth_user(django_user, target_db):
    """
    Sync Django auth_user from master to company database.

    Args:
        django_user: DjangoUser instance from master DB
        target_db: Company database name

    Returns:
        DjangoUser instance in target database
    """
    from django.contrib.auth.models import User as DjangoUser

    try:
        # Check if user already exists in target database
        existing_user = DjangoUser.objects.using(target_db).filter(
            username=django_user.username
        ).first()

        if existing_user:
            # Update existing user
            existing_user.email = django_user.email
            existing_user.first_name = django_user.first_name
            existing_user.last_name = django_user.last_name
            existing_user.password = django_user.password
            existing_user.is_active = django_user.is_active
            existing_user.is_staff = django_user.is_staff
            existing_user.is_superuser = django_user.is_superuser
            existing_user.save(using=target_db)

            logger.info(f"[OK] Updated auth_user in {target_db}: {django_user.username}")
            return existing_user
        else:
            # Create new user
            new_user = DjangoUser.objects.using(target_db).create(
                id=django_user.id,
                username=django_user.username,
                email=django_user.email,
                first_name=django_user.first_name,
                last_name=django_user.last_name,
                password=django_user.password,
                is_active=django_user.is_active,
                is_staff=django_user.is_staff,
                is_superuser=django_user.is_superuser,
                date_joined=django_user.date_joined
            )

            logger.info(f"[OK] Created auth_user in {target_db}: {django_user.username}")
            return new_user

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to sync auth_user to {target_db}: {e}", exc_info=True
        )
        raise


def populate_permission_types(target_db):
    """
    Populate PermissionType table in company database.

    Args:
        target_db: Company database name
    """
    from user.models import PermissionType
    from django.db import transaction

    try:
        permission_types = [
            {'id': 1, 'name': 'Full Access'},
            {'id': 2, 'name': 'View'},
            {'id': 3, 'name': 'Create'},
            {'id': 4, 'name': 'Edit'},
            {'id': 5, 'name': 'Delete'},
        ]

        with transaction.atomic(using=target_db):
            for perm_type in permission_types:
                PermissionType.objects.using(target_db).update_or_create(
                    id=perm_type['id'],
                    defaults={'name': perm_type['name']}
                )

        logger.info(f"[OK] Populated {len(permission_types)} permission types in {target_db}")
        return True

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to populate permission types in {target_db}: {e}",
            exc_info=True
        )
        raise


def ensure_required_modules(target_db):
    """
    Backfill module rows that may be missing in older company databases.

    This keeps legacy company DBs aligned when new modules are introduced
    after the company was originally provisioned.
    """
    from user.models import Module
    from django.db import transaction

    required_modules = [
        {'id': 79, 'name': 'System settings Period Lock'},
        {'id': 80, 'name': 'Masters Category'},
        {'id': 81, 'name': 'Masters Type'},
        {'id': 82, 'name': 'Sales Return'},
        {'id': 83, 'name': 'Purchase Return'},
        {'id': 84, 'name': 'Sales Performa Invoice'},
        {'id': 85, 'name': 'Sales Dashboard'},
        {'id': 86, 'name': 'Purchase Dashboard'},
        {'id': 87, 'name': 'Masters Dashboard'},
        {'id': 88, 'name': 'System settings Other'},
        {'id': 89, 'name': 'Price List'},
        {'id': 90, 'name': 'Sales Eway Bill'},
        {'id': 91, 'name': 'Banking'},
        {'id': 92, 'name': 'Bank Reconciliation'},
    ]

    created_count = 0
    updated_count = 0

    try:
        with transaction.atomic(using=target_db):
            for module_data in required_modules:
                existing_by_name = Module.objects.using(target_db).filter(
                    name=module_data['name']
                ).first()
                if existing_by_name:
                    if existing_by_name.id != module_data['id']:
                        logger.warning(
                            "[WARNING] Module '%s' already exists in %s with id=%s",
                            module_data['name'],
                            target_db,
                            existing_by_name.id,
                        )
                    continue

                existing_by_id = Module.objects.using(target_db).filter(
                    id=module_data['id']
                ).first()

                if existing_by_id:
                    if existing_by_id.name != module_data['name']:
                        existing_by_id.name = module_data['name']
                        existing_by_id.save(using=target_db, update_fields=['name'])
                        updated_count += 1
                    continue

                Module.objects.using(target_db).create(
                    id=module_data['id'],
                    name=module_data['name'],
                )
                created_count += 1

        if created_count or updated_count:
            logger.info(
                "[OK] Backfilled modules in %s (created=%s, updated=%s)",
                target_db,
                created_count,
                updated_count,
            )
        return created_count + updated_count

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to backfill required modules in {target_db}: {e}",
            exc_info=True,
        )
        raise


def ensure_admin_role_permissions_up_to_date(target_db):
    """
    Ensure legacy company DBs get permissions for any newly backfilled modules.
    """
    from user.models import Role

    try:
        admin_roles = Role.objects.using(target_db).filter(role_name__iexact='Admin')
        refreshed = 0

        for role in admin_roles:
            create_admin_role_permissions(target_db, role.id)
            refreshed += 1

        if refreshed:
            logger.info(
                "[OK] Refreshed admin role permissions for %s role(s) in %s",
                refreshed,
                target_db,
            )
        return refreshed

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to refresh admin role permissions in {target_db}: {e}",
            exc_info=True,
        )
        raise


def ensure_sales_return_permissions(target_db):
    """
    Backfill Sales Return role permissions for legacy roles.

    Older company DBs can have the module row without corresponding
    RolePermission rows. Copy the permission types from existing Sales
    transaction modules when Sales Return is missing.
    """
    from django.db import transaction
    from user.models import Module, Role, RolePermission

    source_module_names = [
        'Sales Delivery',
        'Sales Invoice',
        'Sales Orders',
        'Sales Quotation',
        'Sales Payments Received',
    ]

    try:
        sales_return_module = Module.objects.using(target_db).filter(
            name='Sales Return'
        ).first()
        if not sales_return_module:
            return 0

        source_modules = list(
            Module.objects.using(target_db).filter(name__in=source_module_names)
        )
        if not source_modules:
            return 0

        created_count = 0
        with transaction.atomic(using=target_db):
            for role in Role.objects.using(target_db).all():
                existing_perm_ids = set(
                    RolePermission.objects.using(target_db).filter(
                        role=role,
                        module=sales_return_module,
                    ).values_list('permission_type_id', flat=True)
                )
                if existing_perm_ids:
                    continue

                source_perms = RolePermission.objects.using(target_db).filter(
                    role=role,
                    module__in=source_modules,
                    allowed=1,
                ).select_related('permission_type')

                perm_type_ids = []
                for rp in source_perms:
                    if rp.permission_type_id not in perm_type_ids:
                        perm_type_ids.append(rp.permission_type_id)

                for permission_type_id in perm_type_ids:
                    RolePermission.objects.using(target_db).get_or_create(
                        role=role,
                        module=sales_return_module,
                        permission_type_id=permission_type_id,
                        defaults={'allowed': True},
                    )
                    created_count += 1

        if created_count:
            logger.info(
                "[OK] Backfilled %s Sales Return role permissions in %s",
                created_count,
                target_db,
            )
        return created_count

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to backfill Sales Return permissions in {target_db}: {e}",
            exc_info=True,
        )
        raise


def ensure_purchase_return_permissions(target_db):
    """
    Backfill Purchase Return role permissions for legacy roles.

    Older company DBs can have the module row without corresponding
    RolePermission rows. Copy the permission types from existing Purchase
    transaction modules when Purchase Return is missing.
    """
    from django.db import transaction
    from user.models import Module, Role, RolePermission

    source_module_names = [
        'Purchase Bills',
        'Purchase Delivery',
        'Purchase Order',
        'Purchase Payments Made',
        'Purchase Expenses',
    ]

    try:
        purchase_return_module = Module.objects.using(target_db).filter(
            name='Purchase Return'
        ).first()
        if not purchase_return_module:
            return 0

        source_modules = list(
            Module.objects.using(target_db).filter(name__in=source_module_names)
        )
        if not source_modules:
            return 0

        created_count = 0
        with transaction.atomic(using=target_db):
            for role in Role.objects.using(target_db).all():
                existing_perm_ids = set(
                    RolePermission.objects.using(target_db).filter(
                        role=role,
                        module=purchase_return_module,
                    ).values_list('permission_type_id', flat=True)
                )
                if existing_perm_ids:
                    continue

                source_perms = RolePermission.objects.using(target_db).filter(
                    role=role,
                    module__in=source_modules,
                    allowed=1,
                ).select_related('permission_type')

                perm_type_ids = []
                for rp in source_perms:
                    if rp.permission_type_id not in perm_type_ids:
                        perm_type_ids.append(rp.permission_type_id)

                for permission_type_id in perm_type_ids:
                    RolePermission.objects.using(target_db).get_or_create(
                        role=role,
                        module=purchase_return_module,
                        permission_type_id=permission_type_id,
                        defaults={'allowed': True},
                    )
                    created_count += 1

        if created_count:
            logger.info(
                "[OK] Backfilled %s Purchase Return role permissions in %s",
                created_count,
                target_db,
            )
        return created_count

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to backfill Purchase Return permissions in {target_db}: {e}",
            exc_info=True,
        )
        raise


def ensure_sales_performa_invoice_permissions(target_db):
    """
    Backfill Sales Performa Invoice role permissions for legacy roles.

    Older company DBs can have the module row without corresponding
    RolePermission rows. Copy the permission types from existing Sales
    transaction modules when Sales Performa Invoice is missing.
    """
    from django.db import transaction
    from user.models import Module, Role, RolePermission

    source_module_names = [
        'Sales Invoice',
        'Sales Orders',
        'Sales Quotation',
        'Sales Delivery',
        'Sales Payments Received',
    ]

    try:
        sales_performa_module = Module.objects.using(target_db).filter(
            name='Sales Performa Invoice'
        ).first()
        if not sales_performa_module:
            return 0

        source_modules = list(
            Module.objects.using(target_db).filter(name__in=source_module_names)
        )
        if not source_modules:
            return 0

        created_count = 0
        with transaction.atomic(using=target_db):
            for role in Role.objects.using(target_db).all():
                existing_perm_ids = set(
                    RolePermission.objects.using(target_db).filter(
                        role=role,
                        module=sales_performa_module,
                    ).values_list('permission_type_id', flat=True)
                )
                if existing_perm_ids:
                    continue

                source_perms = RolePermission.objects.using(target_db).filter(
                    role=role,
                    module__in=source_modules,
                    allowed=1,
                ).select_related('permission_type')

                perm_type_ids = []
                for rp in source_perms:
                    if rp.permission_type_id not in perm_type_ids:
                        perm_type_ids.append(rp.permission_type_id)

                for permission_type_id in perm_type_ids:
                    RolePermission.objects.using(target_db).get_or_create(
                        role=role,
                        module=sales_performa_module,
                        permission_type_id=permission_type_id,
                        defaults={'allowed': True},
                    )
                    created_count += 1

        if created_count:
            logger.info(
                "[OK] Backfilled %s Sales Performa Invoice role permissions in %s",
                created_count,
                target_db,
            )
        return created_count

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to backfill Sales Performa Invoice permissions in {target_db}: {e}",
            exc_info=True,
        )
        raise

def ensure_sales_eway_bill_permissions(target_db):
    """
    Backfill Sales Eway Bill role permissions for legacy roles.
    Older company DBs can have the module row without corresponding
    RolePermission rows. Copy the permission types from existing Sales
    transaction modules when Sales Eway Bill is missing.
    """
    from django.db import transaction
    from user.models import Module, Role, RolePermission

    source_module_names = [
        'Sales Invoice',
        'Sales Orders',
        'Sales Quotation',
        'Sales Delivery',
        'Sales Payments Received',
    ]

    try:
        eway_bill_module = Module.objects.using(target_db).filter(
            name='Sales Eway Bill'
        ).first()
        if not eway_bill_module:
            return 0

        source_modules = list(
            Module.objects.using(target_db).filter(name__in=source_module_names)
        )
        if not source_modules:
            return 0

        created_count = 0
        with transaction.atomic(using=target_db):
            for role in Role.objects.using(target_db).all():
                existing_perm_ids = set(
                    RolePermission.objects.using(target_db).filter(
                        role=role,
                        module=eway_bill_module,
                    ).values_list('permission_type_id', flat=True)
                )
                if existing_perm_ids:
                    continue

                source_perms = RolePermission.objects.using(target_db).filter(
                    role=role,
                    module__in=source_modules,
                    allowed=1,
                ).select_related('permission_type')

                perm_type_ids = []
                for rp in source_perms:
                    if rp.permission_type_id not in perm_type_ids:
                        perm_type_ids.append(rp.permission_type_id)

                for permission_type_id in perm_type_ids:
                    RolePermission.objects.using(target_db).get_or_create(
                        role=role,
                        module=eway_bill_module,
                        permission_type_id=permission_type_id,
                        defaults={'allowed': True},
                    )
                    created_count += 1

        if created_count:
            logger.info(
                "[OK] Backfilled %s Sales Eway Bill role permissions in %s",
                created_count,
                target_db,
            )
        return created_count

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to backfill Sales Eway Bill permissions in {target_db}: {e}",
            exc_info=True,
        )
        raise


def populate_modules_from_license(target_db, allowed_modules):
    """
    Populate Module table in company database based on license key.

    Args:
        target_db: Company database name
        allowed_modules: List of module names allowed by license key
                        Pass None or empty list for full license (all modules)
    """
    from user.models import Module
    from django.db import transaction

    try:
        ensure_required_modules(target_db)

        all_modules = {
            'Accounts': [
                {'id': 51, 'name': 'Accounts Chart of Accounts'},
                {'id': 52, 'name': 'Accounts Journal'},
            ],
            'Banking': [
                {'id': 91, 'name': 'Banking'},
                {'id': 92, 'name': 'Bank Reconciliation'},
            ],
            'CRM': [
                {'id': 49, 'name': 'CRM Dashboard'},
                {'id': 46, 'name': 'CRM Follow Ups'},
                {'id': 44, 'name': 'CRM Lead'},
                {'id': 47, 'name': 'CRM Lost reason'},
                {'id': 45, 'name': 'CRM Opportunity'},
                {'id': 48, 'name': 'CRM Presale'},
            ],
            'HR': [
                {'id': 25, 'name': 'HR Dashboard'},
                {'id': 26, 'name': 'HR Employee'},
                {'id': 27, 'name': 'HR masters'},
                {'id': 28, 'name': 'HR Recruitments'},
            ],
            'Masters': [
                {'id': 60, 'name': 'Masters Brand'},
                {'id': 80, 'name': 'Masters Category'},
                {'id': 81, 'name': 'Masters Type'},
                {'id': 65, 'name': 'Masters Payment Terms'},
                {'id': 64, 'name': 'Masters Stock'},
                {'id': 59, 'name': 'Masters Taxes'},
                {'id': 61, 'name': 'Masters Unit'},
                {'id': 58, 'name': 'Masters User Roles'},
                {'id': 57, 'name': 'Masters Users'},
                {'id': 62, 'name': 'Masters vendor'},
                {'id': 63, 'name': 'Masters Warehouse'},
                {'id': 36, 'name': 'Masters Customer'},
                {'id': 35, 'name': 'Masters Items'},
                {'id': 87, 'name': 'Masters Dashboard'},
            ],
            'Purchase': [
                {'id': 73, 'name': 'Purchase Bills'},
                {'id': 76, 'name': 'Purchase Delivery'},
                {'id': 75, 'name': 'Purchase Expenses'},
                {'id': 72, 'name': 'Purchase Order'},
                {'id': 74, 'name': 'Purchase Payments Made'},
                {'id': 83, 'name': 'Purchase Return'},
                {'id': 86, 'name': 'Purchase Dashboard'},
            ],
            'Reports': [
                {'id': 53, 'name': 'Reports Balance Sheet'},
                {'id': 54, 'name': 'Reports Profit and Loss'},
                {'id': 55, 'name': 'Reports Trial Balance'},
                {'id': 78, 'name': 'Reports Cash Flow'},
            ],
            'Sales': [
                {'id': 82, 'name': 'Sales Return'},
                {'id': 77, 'name': 'Sales Delivery'},
                {'id': 50, 'name': 'Sales Invoice'},
                {'id': 11, 'name': 'Sales Orders'},
                {'id': 56, 'name': 'Sales Payments Received'},
                {'id': 37, 'name': 'Sales Quotation'},
                {'id': 84, 'name': 'Sales Performa Invoice'},
                {'id': 85, 'name': 'Sales Dashboard'},
                {'id': 89, 'name': 'Price List'},
                {'id': 90, 'name': 'Sales Eway Bill'},
            ],
            'System': [
                {'id': 71, 'name': 'System settings'},
                {'id': 66, 'name': 'System settings Company'},
                {'id': 67, 'name': 'System settings Email Configuration'},
                {'id': 68, 'name': 'System settings Email Templates'},
                {'id': 69, 'name': 'System settings SMS Configuration'},
                {'id': 70, 'name': 'System settings SMS Templates'},
                {'id': 79, 'name': 'System settings Period Lock'},
                {'id': 88, 'name': 'System settings Other'},
            ],
        }

        modules_to_add = []

        if not allowed_modules or len(allowed_modules) == 0:
            logger.info(f"Full license detected - adding all modules to {target_db}")
            for module_list in all_modules.values():
                modules_to_add.extend(module_list)
        else:
            logger.info(f"License modules: {allowed_modules} for {target_db}")
            for module_category in allowed_modules:
                if module_category in all_modules:
                    modules_to_add.extend(all_modules[module_category])
                    logger.info(f"Adding {module_category} modules to {target_db}")
                else:
                    logger.warning(
                        f"[WARNING] Unknown module category in license: {module_category}"
                    )

        with transaction.atomic(using=target_db):
            for module_data in modules_to_add:
                Module.objects.using(target_db).update_or_create(
                    id=module_data['id'],
                    defaults={'name': module_data['name']}
                )

        logger.info(f"[OK] Populated {len(modules_to_add)} modules in {target_db}")
        return True

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to populate modules in {target_db}: {e}", exc_info=True
        )
        raise


def create_admin_role_permissions(target_db, role_id):
    """
    Automatically create RolePermissions for Admin role with Full Access.
    Creates permissions for View, Create, Edit, Delete, and Full Access.

    Args:
        target_db: Company database name
        role_id: Admin role ID
    """
    from user.models import Module, PermissionType, RolePermission
    from django.db import transaction

    try:
        modules = Module.objects.using(target_db).all()

        if not modules.exists():
            logger.warning(f"[WARNING] No modules found in {target_db} to create permissions")
            return False

        try:
            permission_types = PermissionType.objects.using(target_db).filter(
                id__in=[1, 2, 3, 4, 5]
            )
            if permission_types.count() < 5:
                logger.error(
                    f"[ERROR] Not all required permission types found in {target_db}"
                )
                return False
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to retrieve permission types in {target_db}: {e}"
            )
            return False

        permissions_created = 0
        with transaction.atomic(using=target_db):
            for module in modules:
                for perm_type in permission_types:
                    existing = RolePermission.objects.using(target_db).filter(
                        role_id=role_id,
                        module=module,
                        permission_type=perm_type
                    ).first()

                    if not existing:
                        RolePermission.objects.using(target_db).create(
                            role_id=role_id,
                            module=module,
                            permission_type=perm_type,
                            allowed=1
                        )
                        permissions_created += 1
                    else:
                        if existing.allowed != 1:
                            existing.allowed = 1
                            existing.save(using=target_db)
                            logger.debug(
                                f"Updated permission allowed status for role {role_id}, "
                                f"module {module.name}, perm {perm_type.name}"
                            )

        logger.info(
            f"[OK] Created {permissions_created} role permissions for Admin in {target_db}"
        )
        return True

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to create admin role permissions in {target_db}: {e}",
            exc_info=True
        )
        raise


def generate_registration_code(company_name, company_id, length=4):
    """
    Generate a meaningful, readable company code for login URLs.

    Format: COMPANYNAME-YEAR-XXXX
    Examples:
        - "ABC Corp"      → ABC-2026-K7M2
        - "Tech Solutions"→ TECHSOL-2026-P9QR
        - "My Business"   → MYBUSINE-2026-X3TY

    Args:
        company_name (str): Company name
        company_id (int): Company ID (unused, kept for signature compatibility)
        length (int): Length of random suffix (default: 4)

    Returns:
        str: Unique company code
    """
    import secrets
    import string
    from datetime import datetime
    from company.models import Company

    # Clean company name — letters/digits only, uppercase, max 8 chars
    clean_name = re.sub(r'[^A-Za-z0-9]', '', company_name).upper()[:8]

    # Current year
    year = datetime.now().year

    # Random alphanumeric suffix (uppercase only, easy to read/type)
    # Exclude visually ambiguous chars: 0, O, I, 1
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

    for _ in range(50):
        suffix = ''.join(secrets.choice(alphabet) for _ in range(length))
        code = f"{clean_name}-{year}-{suffix}"

        if not Company.objects.filter(company_code=code).exists():
            logger.info(f"[OK] Generated company code: {code}")
            return code

    # Fallback: longer suffix to guarantee uniqueness
    fallback_suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    fallback_code = f"{clean_name}-{year}-{fallback_suffix}"
    logger.warning(f"[WARN] Used fallback company code: {fallback_code}")
    return fallback_code
