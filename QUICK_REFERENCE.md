# Database Cleanup - Quick Reference Guide

## Quick Start

### Check Current Status
```bash
python manage.py cleanup_status
```

### Preview What Will Be Deleted
```bash
python manage.py delete_expired_trial_databases --dry-run
```

### Execute Cleanup (Default: Complete Removal)
```bash
python manage.py delete_expired_trial_databases
```

### Execute Cleanup (Archive Mode: Keep Records)
```bash
python manage.py delete_expired_trial_databases --keep-entries
```

---

## Common Tasks

### 1. View Cleanup Status
```bash
# Quick status
python manage.py cleanup_status

# Detailed summary
python manage.py cleanup_status --summary

# Export as report
python manage.py cleanup_status --export txt
python manage.py cleanup_status --export csv > report.csv
python manage.py cleanup_status --export json > report.json
```

### 2. Manually Delete a Company
```bash
# Complete removal
python manage.py cleanup_status --delete 123

# Archive mode
python manage.py cleanup_status --delete 123 --keep-entry

# Force removal (ignore active licenses)
python manage.py cleanup_status --delete 123 --force
```

### 3. Check Specific Company Status
```python
# In Python/Django shell:
python manage.py shell

from Lyraerp.utils.cleanup_utils import *

# Check if company is expired
expired = get_expired_companies()

# Check if eligible for deletion
eligible = get_companies_pending_deletion()

# Get summary
summary = get_cleanup_summary()
print(summary)
```

### 4. Schedule Automatic Cleanup
The cleanup runs automatically as part of the scheduler:

**Edit** `Lyraerp/scheduler.py` in `_run_all_jobs()`:

```python
# Default - Complete removal (recommended)
delete_expired_trial_databases_job()

# Or - Archive mode
delete_expired_trial_databases_job(remove_company_entry=False)
```

---

## Understanding the Modes

### Complete Removal (Default) ✓ Recommended
```bash
python manage.py delete_expired_trial_databases
```
- Database is deleted ✓
- Company entry is DELETED ✓
- Clean database ✓
- No audit trail ✗

### Archive Mode
```bash
python manage.py delete_expired_trial_databases --keep-entries
```
- Database is deleted ✓
- Company entry is MARKED as deleted ✓
- Clean database ✓
- Audit trail available ✓

---

## Timeline

```
Day 0: Expiry
  ↓
Days 1-7: Grace Period
  • Database still accessible
  • Warning emails sent
  • Can renew to prevent deletion
  ↓
Day 8+: Deleted
  • Database removed
  • Company entry removed (or archived)
```

---

## Troubleshooting

### "Company has active license" error
**Cause**: Company has valid active license
**Solution**: 
- Renew/extend the license, OR
- Use `--force` flag to override

### "Database not found" error
**Cause**: Database already deleted or doesn't exist
**Solution**:
- Check status with `cleanup_status`
- Verify company ID is correct

### Companies not being deleted automatically
**Cause**: 
- Grace period not passed (less than 7 days)
- Company has active license
- Scheduler not running
**Solution**:
- Check with `cleanup_status`
- Verify scheduler job is enabled
- Run manually with `--dry-run` to test

### Need to restore deleted company
**Solution**: Restore from backup
```bash
# Restore database
mysql < /backups/company_db.sql

# Add Company entry if needed
python manage.py shell
from company.models import Company
Company.objects.create(name='...', db_name='...', ...)
```

---

## Important Notes

⚠️ **Before Running Cleanup**
1. Back up main database
2. Back up all company databases
3. Test with `--dry-run` first
4. Verify grace period has passed

✅ **After Cleanup**
1. Verify deletions completed
2. Check error logs
3. Confirm database count reduced

---

## Configuration

### Grace Period (Days Before Deletion)
**File**: `Lyraerp/scheduler.py`, line 865

Change:
```python
if not expiry_date or now.date() < expiry_date + timedelta(days=7):
```

To (example: 14 days):
```python
if not expiry_date or now.date() < expiry_date + timedelta(days=14):
```

### Default Deletion Mode
**File**: `Lyraerp/scheduler.py`, in `_run_all_jobs()`

Change:
```python
# For complete removal (default)
delete_expired_trial_databases_job(remove_company_entry=True)

# For archive mode
delete_expired_trial_databases_job(remove_company_entry=False)
```

---

## File Reference

| File | Purpose |
|------|---------|
| `Lyraerp/scheduler.py` | Core cleanup function |
| `Lyraerp/management/commands/delete_expired_trial_databases.py` | CLI command |
| `Lyraerp/management/commands/cleanup_status.py` | Status management |
| `Lyraerp/utils/cleanup_utils.py` | Utility functions |
| `cleanup_config.py` | Configuration options |
| `CLEANUP_DATABASE_FEATURE.md` | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | Technical details |

---

## API Reference

### Python Functions

```python
from Lyraerp.utils.cleanup_utils import *

# Get expired companies
expired = get_expired_companies()

# Get companies in grace period
in_grace = get_companies_in_grace_period()

# Get companies eligible for deletion
eligible = get_companies_pending_deletion()

# Get summary
summary = get_cleanup_summary()

# Export report
report = export_cleanup_report(format='json')  # json, csv, or txt

# Manually delete
result = manually_delete_company(
    company_id=123,
    remove_entry=True,      # True = delete, False = archive
    force=False             # True = ignore license check
)
```

### Management Commands

```bash
# Deletion
python manage.py delete_expired_trial_databases [--dry-run] [--keep-entries]

# Status
python manage.py cleanup_status [--summary] [--export FORMAT] [--delete ID] [--force]
```

---

## Common Scenarios

### Scenario: Weekly Cleanup Review
```bash
# Check status
python manage.py cleanup_status

# Preview what will be deleted
python manage.py delete_expired_trial_databases --dry-run

# If happy, execute
python manage.py delete_expired_trial_databases

# Verify results
python manage.py cleanup_status
```

### Scenario: Monthly Report
```bash
# Generate report
python manage.py cleanup_status --export csv > monthly_report.csv

# Share with stakeholders
```

### Scenario: Emergency Deletion
```bash
# Force delete a specific company (ignore license check)
python manage.py cleanup_status --delete 456 --force

# Confirm deletion
python manage.py cleanup_status
```

### Scenario: Compliance/Audit Trail
```bash
# Use archive mode to keep records
python manage.py delete_expired_trial_databases --keep-entries

# All deletions create audit trail
```

---

## Log Monitoring

### Success
```
[SCHEDULER] JOB 5 - Completely removed database and Company entry 'ClientName' (xyz_2026) after license expiry
```

### Archive
```
[SCHEDULER] JOB 5 - Deleted license database 'xyz_2026' for 'ClientName' (Company entry archived)
```

### Error
```
[SCHEDULER] JOB 5 - Failed to remove Company entry for 'ClientName': <error details>
```

---

## Version & Status

- **Version**: 1.0
- **Release Date**: August 31, 2026
- **Status**: Production Ready
- **Backward Compatible**: Yes

---

## Support

For help:
1. Check logs: `/logs/django.log`
2. Run `cleanup_status` to verify state
3. Use `--dry-run` to test
4. Review CLEANUP_DATABASE_FEATURE.md for details
