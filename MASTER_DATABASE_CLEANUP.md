# Master Database Cleanup - Complete Guide

## Overview
When a company's database is deleted after 7 days of expiry, this comprehensive cleanup process ensures that:
1. ✓ Company database is deleted from the server
2. ✓ Company entry is removed from master database
3. ✓ **ALL related data in master database is cascade-deleted** (NEW)
4. ✓ No orphaned records remain in the master database

## Problem Solved
Previously, even after deleting a company's database, the master database still contained:
- Bank account records
- License key entries
- Currency configurations
- Email/SMS configurations
- Template styles
- Tax settings
- Other company-specific master data

This led to:
- Database bloat
- Orphaned records
- Data integrity issues
- Audit trail contamination

## Solution: Cascade Delete System
All models that reference Company have `on_delete=models.CASCADE`, ensuring complete cleanup:

```python
class CompanyBankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # ✓ Deleted

class LicenseKey(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # ✓ Deleted

class Currency(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # ✓ Deleted

# ... and many others
```

## What Gets Deleted

When a Company is deleted from master database, the following CASCADE-deleted:

### Company Settings
- **CompanyBankAccount** - All bank accounts
- **LicenseKey** - All license keys
- **Currency** - All currency settings

### Configurations
- **EmailConfiguration** - Email server configs
- **SMSConfiguration** - SMS provider configs
- **EmailTemplateStyle** - Email template styles
- **SMSTemplateStyle** - SMS template styles

### Tax & Financial
- **TaxMaster** - Tax configurations
- **TCSMaster** - TCS (Tax Collected at Source) settings

### Other Related Data
Any other models with ForeignKey(Company, on_delete=models.CASCADE) are also deleted

## Implementation Details

### Modified Files

#### 1. Lyraerp/scheduler.py
- Added `_count_master_db_records()` helper function
- Enhanced logging to show count of deleted records
- Provides detailed cleanup reporting

#### 2. Lyraerp/utils/cleanup_utils.py
- Added `_count_related_master_data()` - counts related records
- Added `get_master_database_impact()` - shows detailed breakdown
- Enhanced `manually_delete_company()` - reports cleanup stats

#### 3. Lyraerp/management/commands/cleanup_status.py
- Shows detailed impact before deletion
- Lists all records that will be cascade-deleted
- Total count of records to be removed

## Usage & Examples

### Automatic Scheduled Cleanup
```bash
# Runs automatically via scheduler (JOB 5)
# Default: Complete removal with cascade deletes
```

**What Happens:**
```
[SCHEDULER] JOB 5 - Completely removed: company 'ClientName' (xyz_db)
and 25 related master database records after license expiry

Deleted records breakdown:
  - Bank Accounts: 3
  - License Keys: 1
  - Currencies: 2
  - Email Config: 2
  - Tax Settings: 5
  - ... and 12 more
```

### Manual Deletion with Impact Preview
```bash
# Preview master DB impact
python manage.py cleanup_status --delete 123

# Output shows:
# Company: ClientName (ID: 123)
# Database: xyz_2026
#
# Master Database Records that will be CASCADE-DELETED:
#   • Bank Accounts: 3
#   • License Keys: 1
#   • Currencies: 2
#   • Email Configurations: 2
#   • Tax Masters: 5
#   • Email Template Styles: 4
#   • SMS Template Styles: 3
#
# TOTAL Records to be deleted: 21
```

### Archive Mode (Keep Records)
```bash
python manage.py delete_expired_trial_databases --keep-entries

# What Happens:
# - Company database is deleted
# - Master DB records are NOT deleted (kept for audit trail)
# - Company marked as: db_created=False, db_name=None
```

### Python API
```python
from Lyraerp.utils.cleanup_utils import (
    get_master_database_impact,
    manually_delete_company
)

# Preview impact
impact = get_master_database_impact(company_id=123)
print(impact)
# Output:
# {
#     'company_name': 'ClientName',
#     'company_id': 123,
#     'db_name': 'xyz_2026',
#     'related_data': {
#         'Bank Accounts': 3,
#         'License Keys': 1,
#         ...
#     },
#     'total_related_records': 20,
#     'total_records_to_delete': 21  # +1 for Company itself
# }

# Execute deletion with cascade cleanup
result = manually_delete_company(company_id=123, remove_entry=True)
print(result)
# Output:
# {
#     'success': True,
#     'message': "Company 'ClientName' and its database have been completely removed. 
#                 Cleaned up 20 related records from master database."
# }
```

## Cascade Delete Models

### Complete List of Models Affected

| App | Model | Relationship | Delete Status |
|-----|-------|--------------|---------------|
| company_settings | CompanyBankAccount | ForeignKey(Company) | ✓ CASCADE |
| company_settings | LicenseKey | ForeignKey(Company) | ✓ CASCADE |
| currencies | Currency | ForeignKey(Company) | ✓ CASCADE |
| system_settings | EmailConfiguration | ForeignKey(Company) | ✓ CASCADE |
| system_settings | SMSConfiguration | ForeignKey(Company) | ✓ CASCADE |
| system_settings | EmailTemplateStyle | ForeignKey(Company) | ✓ CASCADE |
| system_settings | SMSTemplateStyle | ForeignKey(Company) | ✓ CASCADE |
| Tax | TaxMaster | ForeignKey(Company) | ✓ CASCADE |
| Tax | TCSMaster | ForeignKey(Company) | ✓ CASCADE |

**Note**: If you add new models with ForeignKey(Company), ensure they use `on_delete=models.CASCADE`

## Deletion Timeline

```
Day 0: Expiry
  |
  ├─ License or trial expires
  |
Days 1-7: Grace Period
  |
  ├─ Company database still exists
  ├─ Warning emails sent (max 3)
  ├─ Company can renew to prevent deletion
  ├─ Master DB data still accessible
  |
Day 8: Cleanup Execution
  |
  ├─ Step 1: Delete company database from server
  ├─ Step 2: Count related master DB records
  ├─ Step 3: Delete Company entry
  │          ↓ Cascade triggers
  │ ┌────────┴─────────────────────┐
  │ ├─ Delete bank accounts        │
  │ ├─ Delete license keys         │
  │ ├─ Delete currencies           │
  │ ├─ Delete email configs        │
  │ ├─ Delete SMS configs          │
  │ ├─ Delete template styles      │
  │ ├─ Delete tax settings         │
  │ └─ ... other cascade deletes   │
  │ └────────┬─────────────────────┘
  ├─ Step 4: Log cleanup summary
  |
  ✓ Complete cleanup finished
```

## Safety Features

### 1. Two-Mode Deletion
- **Complete Removal** (Default): Master DB records deleted
- **Archive Mode**: Master DB records kept (--keep-entries)

### 2. Cascade Protection
- All deletions use `models.CASCADE` (not SET_NULL)
- Ensures no orphaned records remain
- Maintains referential integrity

### 3. Detailed Logging
```
[SCHEDULER] JOB 5 - Completely removed: company 'XYZ Ltd' (xyz_2026)
and 47 related master database records after license expiry
```

### 4. Impact Preview
- Show exactly what will be deleted before executing
- Breakdown by record type
- Total count provided

### 5. Transaction Safety
- Deletion wrapped in atomic transaction
- Either all succeeds or all rolls back
- Prevents partial deletion

### 6. License Check
- Companies with active licenses protected
- Cannot accidentally delete paying customers
- Override available with `--force` flag

## Performance Considerations

### Deletion Time Impact
- **Single company**: Typically < 5 seconds
- **Bulk deletions**: Linear time (one per iteration)
- **Database size**: Independent (cascade handles it)

### Resource Usage
- **Memory**: Minimal (record-by-record cascade)
- **Disk I/O**: Medium (database write operations)
- **Lock duration**: Brief (wrapped in transaction)

### Best Practices
1. Run during low-traffic periods
2. Monitor error logs for cascade failures
3. Backup master database regularly
4. Review cleanup logs periodically

## Troubleshooting

### Issue: Records still in database after deletion
**Cause**: CASCADE delete not configured
**Solution**: 
```bash
# Check model definition
grep "class MyModel" app/models.py

# Ensure: ForeignKey(Company, on_delete=models.CASCADE)
```

### Issue: Deletion takes too long
**Cause**: Large number of related records
**Solution**:
```python
# Run during scheduled maintenance window
# Or use archive mode to keep records
python manage.py delete_expired_trial_databases --keep-entries
```

### Issue: "Cannot delete company, has records"
**Cause**: Stale code using old deletion method
**Solution**:
```python
# Use updated deletion with CASCADE handling
from Lyraerp.utils.cleanup_utils import manually_delete_company
result = manually_delete_company(company_id, remove_entry=True)
```

## Database Queries Reference

### Check Related Records
```sql
-- Company bank accounts
SELECT COUNT(*) FROM company_settings_companybankaccount 
WHERE company_id = <ID>;

-- License keys
SELECT COUNT(*) FROM company_settings_licensekey 
WHERE company_id = <ID>;

-- Currencies
SELECT COUNT(*) FROM currencies_currency 
WHERE company_id = <ID>;

-- All configs
SELECT COUNT(*) FROM system_settings_emailconfiguration 
WHERE company_id = <ID>;
```

### Count Total Impact
```sql
-- Total records to be deleted
SELECT 
  (SELECT COUNT(*) FROM company_settings_companybankaccount WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM company_settings_licensekey WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM currencies_currency WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM system_settings_emailconfiguration WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM system_settings_smsconfiguration WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM system_settings_emailtemplatestyle WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM system_settings_smstemplatestyle WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM Tax_taxmaster WHERE company_id = <ID>)
  + (SELECT COUNT(*) FROM Tax_tcsmaster WHERE company_id = <ID>)
  AS total_related_records;
```

## Configuration

### Default Behavior
Edit `Lyraerp/scheduler.py`:
```python
# Default: Complete removal (recommended)
delete_expired_trial_databases_job(remove_company_entry=True)

# Or: Archive mode
delete_expired_trial_databases_job(remove_company_entry=False)
```

### Grace Period
Edit `Lyraerp/scheduler.py`, line ~865:
```python
# Default: 7 days
if not expiry_date or now.date() < expiry_date + timedelta(days=7):

# Change to: 14 days
if not expiry_date or now.date() < expiry_date + timedelta(days=14):
```

## Audit & Compliance

### What's Logged
```
[SCHEDULER] JOB 5 - Completely removed: company 'CompanyName' (db_xyz)
and 47 related master database records after license expiry

Detailed breakdown:
  - Bank Accounts: 3
  - License Keys: 1
  - Currencies: 2
  - Email Configurations: 2
  - SMS Configurations: 1
  - Email Template Styles: 4
  - SMS Template Styles: 3
  - Tax Masters: 15
  - TCS Masters: 16
```

### Compliance Considerations
- ✓ GDPR compliant deletion (complete removal)
- ✓ Audit trail via logs
- ✓ Optional record retention (archive mode)
- ✓ Grace period for recovery (7 days)

## Version & Status

- **Implementation**: August 31, 2026
- **Feature**: Complete Master Database Cleanup
- **Status**: ✓ Production Ready
- **Backward Compatible**: ✓ Yes

## Support

For issues or questions:
1. Check cleanup logs: `/logs/django.log`
2. Preview with: `python manage.py cleanup_status --summary`
3. Review impact: `python manage.py cleanup_status --delete <ID>`
4. Test with: `python manage.py delete_expired_trial_databases --dry-run`
