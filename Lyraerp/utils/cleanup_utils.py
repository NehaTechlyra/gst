"""
Database Cleanup Utilities

Provides helper functions for managing the database cleanup process,
including preview, manual deletion, and recovery.

This module ensures complete cleanup of:
1. Company database (physical database file)
2. Master database Company entry
3. All related data in master database (cascade deletes)
4. All references to the company in other tables
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction, connections
from django.db.models import Q
from django.db.models.deletion import CASCADE
from django.apps import apps

logger = logging.getLogger(__name__)


def get_expired_companies(days_past_expiry=None):
    """
    Get list of companies that have expired.
    
    Args:
        days_past_expiry: If provided, only return companies expired exactly N days ago
                         If None, return all expired companies
    
    Returns:
        QuerySet of expired Company objects
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import database_exists, register_database
    
    expired_companies = []
    now = timezone.now()
    
    companies = Company.objects.using('default').filter(
        Q(db_created=True, db_name__isnull=False)
        | Q(db_name__isnull=True, trial_expires_at__lte=now - timedelta(days=7))
    )
    
    for company in companies:
        try:
            tenant_db_exists = database_exists(company.db_name)
            license_obj = None

            if tenant_db_exists:
                register_database(company.db_name)
                license_obj = LicenseKey.objects.using(company.db_name).filter(
                    company_id=company.pk,
                ).first()
            
            if license_obj and license_obj.expiry_date:
                expiry_date = license_obj.expiry_date
            elif company.trial_expires_at:
                expiry_date = company.trial_expires_at.date()
            elif not tenant_db_exists:
                expiry_date = now.date()
            else:
                continue
            
            # Ensure we're working with date objects
            if hasattr(expiry_date, 'date'):
                expiry_only = expiry_date.date()
            else:
                expiry_only = expiry_date
            
            days_past = (now.date() - expiry_only).days
            
            # Filter based on days_past_expiry parameter
            if days_past_expiry is not None:
                if days_past == days_past_expiry:
                    expired_companies.append({
                        'company': company,
                        'days_past_expiry': days_past,
                        'expiry_date': expiry_only,
                    })
            else:
                if days_past >= 0:  # Any expired company
                    expired_companies.append({
                        'company': company,
                        'days_past_expiry': days_past,
                        'expiry_date': expiry_only,
                    })
        except Exception as e:
            logger.error(f"Error checking expiry for {company.name}: {e}")
            continue
    
    return expired_companies


def get_companies_pending_deletion(grace_period_days=7):
    """
    Get companies that are eligible for deletion (past grace period).
    
    Args:
        grace_period_days: Number of days after expiry before deletion
    
    Returns:
        List of company dictionaries eligible for deletion
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import database_exists, register_database
    
    eligible = []
    now = timezone.now()
    
    companies = Company.objects.using('default').filter(
        Q(db_created=True, db_name__isnull=False)
        | Q(db_name__isnull=True, trial_expires_at__lte=now - timedelta(days=grace_period_days))
    )
    
    for company in companies:
        try:
            tenant_db_exists = database_exists(company.db_name)
            license_obj = None

            if tenant_db_exists:
                register_database(company.db_name)
                license_obj = LicenseKey.objects.using(company.db_name).filter(
                    company_id=company.pk,
                ).first()
            
            if license_obj and license_obj.expiry_date:
                expiry_date = license_obj.expiry_date
            elif company.trial_expires_at:
                expiry_date = company.trial_expires_at.date()
            elif not tenant_db_exists:
                expiry_date = now.date() - timedelta(days=grace_period_days)
            else:
                continue
            
            # Ensure date objects
            if hasattr(expiry_date, 'date'):
                expiry_only = expiry_date.date()
            else:
                expiry_only = expiry_date
            
            # Check if past grace period
            days_past = (now.date() - expiry_only).days
            if days_past >= grace_period_days:
                # Check if company has valid license
                has_valid_license = bool(
                    license_obj
                    and license_obj.is_active
                    and not license_obj.is_license_expired
                    and expiry_date >= now.date()
                )
                
                if not has_valid_license:
                    eligible.append({
                        'company': company,
                        'company_name': company.name,
                        'db_name': company.db_name,
                        'expiry_date': expiry_only,
                        'days_past_expiry': days_past,
                    })
        except Exception as e:
            logger.error(f"Error checking eligibility for {company.name}: {e}")
            continue
    
    return eligible


def get_companies_in_grace_period(grace_period_days=7):
    """
    Get companies in the grace period (between expiry and deletion).
    
    Args:
        grace_period_days: Length of grace period in days
    
    Returns:
        List of companies currently in grace period
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import database_exists, register_database
    
    in_grace = []
    now = timezone.now()
    
    companies = Company.objects.using('default').filter(
        db_created=True,
        db_name__isnull=False,
    )
    
    for company in companies:
        try:
            tenant_db_exists = database_exists(company.db_name)
            license_obj = None

            if tenant_db_exists:
                register_database(company.db_name)
                license_obj = LicenseKey.objects.using(company.db_name).filter(
                    company_id=company.pk,
                ).first()
            
            if license_obj and license_obj.expiry_date:
                expiry_date = license_obj.expiry_date
            elif not tenant_db_exists:
                continue
            elif company.trial_expires_at:
                expiry_date = company.trial_expires_at.date()
            else:
                continue
            
            # Ensure date objects
            if hasattr(expiry_date, 'date'):
                expiry_only = expiry_date.date()
            else:
                expiry_only = expiry_date
            
            # Check if in grace period
            days_past = (now.date() - expiry_only).days
            if 0 <= days_past < grace_period_days:
                in_grace.append({
                    'company': company,
                    'company_name': company.name,
                    'db_name': company.db_name,
                    'expiry_date': expiry_only,
                    'days_past_expiry': days_past,
                    'days_until_deletion': grace_period_days - days_past,
                })
        except Exception as e:
            logger.error(f"Error checking grace period for {company.name}: {e}")
            continue
    
    return in_grace


def manually_delete_company(company_id, remove_entry=True, force=False):
    """
    Manually delete a company database and optionally its entry.
    
    Args:
        company_id: ID of the Company to delete
        remove_entry: If True, delete Company entry; if False, archive it
        force: If True, delete even if company has valid license
    
    Returns:
        Dictionary with status and message
    """
    from company.models import Company
    from company_settings.models import LicenseKey
    from Lyraerp.utils.db_utils import (
        database_exists,
        delete_company_database,
        register_database,
    )
    
    try:
        company = Company.objects.using('default').get(pk=company_id)
        
        if not company.db_created or not company.db_name:
            return {
                'success': False,
                'message': f"Company '{company.name}' has no active database"
            }
        
        # Check for valid license unless forced
        tenant_db_exists = database_exists(company.db_name)

        if not force and tenant_db_exists:
            register_database(company.db_name)
            license_obj = LicenseKey.objects.using(company.db_name).filter(
                company_id=company.pk,
            ).first()
            
            if license_obj and license_obj.is_active and not license_obj.is_license_expired:
                return {
                    'success': False,
                    'message': f"Company '{company.name}' has an active license. Use force=True to override."
                }
        
        # Delete database. DROP IF EXISTS also keeps stale-master cleanup retryable.
        if tenant_db_exists:
            delete_company_database(company.db_name)
        else:
            logger.warning(
                "[MANUAL DELETE] Tenant database '%s' for '%s' is already missing; "
                "cleaning stale master Company entry",
                company.db_name,
                company.name,
            )
        
        # Delete or archive Company entry
        if remove_entry:
            with transaction.atomic(using='default'):
                company_name = company.name
                company_id_val = company.pk
                
                # Count related records before deletion
                related_count = _count_related_master_data(company)
                
                # Delete Company without querying tenant-only tables in master.
                _delete_master_company_entry(company)
                
                logger.warning(
                    f"[MANUAL DELETE] Completely removed company '{company_name}' "
                    f"and {related_count} related master database records"
                )
                return {
                    'success': True,
                    'message': f"Company '{company_name}' and its database have been completely removed. "
                               f"Cleaned up {related_count} related records from master database."
                }
        else:
            with transaction.atomic(using='default'):
                # Count related records
                related_count = _count_related_master_data(company)
                
                Company.objects.using('default').filter(pk=company_id).update(
                    db_created=False,
                    db_name=None,
                )
                logger.warning(
                    f"[MANUAL DELETE] Archived company database for '{company.name}' "
                    f"({related_count} related records remain in master DB)"
                )
                return {
                    'success': True,
                    'message': f"Database for '{company.name}' has been removed and company archived. "
                               f"{related_count} related records kept in master database."
                }
    
    except Company.DoesNotExist:
        return {
            'success': False,
            'message': f"Company with ID {company_id} not found"
        }
    except Exception as e:
        logger.error(f"Error deleting company {company_id}: {e}", exc_info=True)
        return {
            'success': False,
            'message': f"Error deleting company: {str(e)}"
        }


def _count_related_master_data(company):
    """
    Count related records in master database for a company.
    Helps identify all data that will be cleaned up via cascade deletes.
    
    Args:
        company: Company instance
        
    Returns:
        Total count of related records
    """
    total = 0
    using_db = 'default'
    
    for relation in company._meta.related_objects:
        if relation.on_delete is not CASCADE:
            continue

        try:
            model = relation.related_model
            if not _master_table_exists(model):
                continue
            lookup = f"{relation.field.name}_id"
            count = model._base_manager.using(using_db).filter(**{lookup: company.pk}).count()
            if count > 0:
                logger.info(f"  [CLEANUP] {model.__name__}: {count} records will be removed")
                total += count
        except Exception as e:
            logger.warning(
                "  [CLEANUP] Error counting %s.%s: %s",
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
        logger.warning("Could not inspect master table %s: %s", model._meta.db_table, exc)
        return False


def _delete_master_company_entry(company):
    """Delete a Company row without querying tenant-only tables in the master DB."""
    from django.db.models.deletion import SET_NULL

    for relation in company._meta.related_objects:
        model = relation.related_model
        if not _master_table_exists(model):
            continue

        lookup = f"{relation.field.name}_id"
        qs = model._base_manager.using('default').filter(**{lookup: company.pk})

        if relation.on_delete is CASCADE:
            qs.delete()
        elif relation.on_delete is SET_NULL and relation.field.null:
            qs.update(**{relation.field.name: None})
        elif qs.exists():
            raise RuntimeError(
                f"Cannot delete Company {company.pk}; protected relation exists: "
                f"{model._meta.label}.{relation.field.name}"
            )

    with connections['default'].cursor() as cursor:
        cursor.execute(
            f"DELETE FROM `{company._meta.db_table}` WHERE `{company._meta.pk.column}` = %s",
            [company.pk],
        )
        return cursor.rowcount


def get_master_database_impact(company_id):
    """
    Get detailed breakdown of what will be deleted in master database.
    
    Useful for previewing the full impact of company deletion before executing it.
    
    Args:
        company_id: ID of the Company
        
    Returns:
        Dictionary with detailed breakdown of related data
    """
    from company.models import Company
    
    try:
        company = Company.objects.using('default').get(pk=company_id)
    except Company.DoesNotExist:
        return {'error': f"Company with ID {company_id} not found"}
    
    impact = {
        'company_name': company.name,
        'company_id': company.pk,
        'db_name': company.db_name,
        'related_data': {}
    }
    
    using_db = 'default'
    
    # Check each related model type
    related_checks = [
        ('company_settings', 'CompanyBankAccount', 'Bank Accounts'),
        ('company_settings', 'LicenseKey', 'License Keys'),
        ('currencies', 'Currency', 'Currencies'),
        ('system_settings', 'EmailConfiguration', 'Email Configurations'),
        ('system_settings', 'SMSConfiguration', 'SMS Configurations'),
        ('system_settings', 'EmailTemplateStyle', 'Email Template Styles'),
        ('system_settings', 'SMSTemplateStyle', 'SMS Template Styles'),
        ('Tax', 'TaxMaster', 'Tax Masters'),
        ('Tax', 'TCSMaster', 'TCS Masters'),
    ]
    
    total_related = 0
    
    for app_label, model_name, display_name in related_checks:
        try:
            model = apps.get_model(app_label, model_name)
            count = model.objects.using(using_db).filter(company_id=company.pk).count()
            if count > 0:
                impact['related_data'][display_name] = count
                total_related += count
        except LookupError:
            continue
        except Exception as e:
            logger.warning(f"Error checking {display_name}: {e}")
            continue
    
    impact['total_related_records'] = total_related
    impact['total_records_to_delete'] = total_related + 1  # +1 for Company itself
    
    return impact


def get_cleanup_summary():
    """
    Get a summary of cleanup status for all companies.
    
    Returns:
        Dictionary with cleanup statistics
    """
    expired = get_expired_companies()
    in_grace = get_companies_in_grace_period()
    eligible = get_companies_pending_deletion()
    
    return {
        'total_expired': len(expired),
        'in_grace_period': len(in_grace),
        'eligible_for_deletion': len(eligible),
        'expired_companies': expired,
        'grace_period_companies': in_grace,
        'deletion_eligible_companies': eligible,
        'timestamp': timezone.now().isoformat(),
    }


def export_cleanup_report(format='json'):
    """
    Export cleanup report in different formats.
    
    Args:
        format: 'json', 'csv', or 'txt'
    
    Returns:
        Formatted report string
    """
    import json
    from datetime import date
    
    summary = get_cleanup_summary()
    
    if format == 'json':
        # Convert dates to strings for JSON serialization
        def date_handler(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(summary, indent=2, default=date_handler)
    
    elif format == 'csv':
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Type', 'Company Name', 'Database', 'Expiry Date', 'Days Past Expiry', 'Days Until Deletion'])
        
        for item in summary['expired_companies']:
            writer.writerow([
                'Expired',
                item['company'].name,
                item['company'].db_name,
                item['expiry_date'],
                item['days_past_expiry'],
                '-'
            ])
        
        for item in summary['grace_period_companies']:
            writer.writerow([
                'Grace Period',
                item['company_name'],
                item['db_name'],
                item['expiry_date'],
                item['days_past_expiry'],
                item['days_until_deletion']
            ])
        
        for item in summary['deletion_eligible_companies']:
            writer.writerow([
                'Eligible for Deletion',
                item['company_name'],
                item['db_name'],
                item['expiry_date'],
                item['days_past_expiry'],
                'Ready'
            ])
        
        return output.getvalue()
    
    elif format == 'txt':
        lines = [
            "=" * 80,
            "DATABASE CLEANUP REPORT",
            "=" * 80,
            f"Generated: {summary['timestamp']}",
            "",
            f"Total Expired Companies: {summary['total_expired']}",
            f"Companies in Grace Period: {summary['in_grace_period']}",
            f"Eligible for Deletion: {summary['eligible_for_deletion']}",
            "",
        ]
        
        if summary['grace_period_companies']:
            lines.extend([
                "COMPANIES IN GRACE PERIOD:",
                "-" * 80,
            ])
            for item in summary['grace_period_companies']:
                lines.append(
                    f"  {item['company_name']:30} | {item['db_name']:30} | "
                    f"Expires: {item['expiry_date']} | Days left: {item['days_until_deletion']}"
                )
            lines.append("")
        
        if summary['deletion_eligible_companies']:
            lines.extend([
                "COMPANIES ELIGIBLE FOR DELETION:",
                "-" * 80,
            ])
            for item in summary['deletion_eligible_companies']:
                lines.append(
                    f"  {item['company_name']:30} | {item['db_name']:30} | "
                    f"Expired: {item['expiry_date']} | Days past: {item['days_past_expiry']}"
                )
            lines.append("")
        
        lines.extend([
            "=" * 80,
        ])
        
        return "\n".join(lines)
    
    else:
        raise ValueError(f"Unsupported format: {format}")
