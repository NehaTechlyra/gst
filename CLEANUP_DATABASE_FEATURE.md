# Database Cleanup Feature - Complete Removal After Expiry

## Overview
This feature ensures that when a database expires and 7 days pass after expiration, the database is completely deleted along with its corresponding entry in the main database.

## How It Works

### Timeline
1. **Day 0 (Expiry Date)**: License or trial expires
2. **Day 1-7 (Grace Period)**: Database still exists; warning emails are sent to company administrators
3. **Day 8+**: Database and Company entry are removed from the system

### Two Deletion Modes

#### 1. **Complete Removal** (Default - Recommended)
- The company's database is deleted from the server
- The Company entry is completely removed from the main database
- All related data associations are cascade-deleted (depends on Django model configurations)
- No audit trail remains in the Company table
- **Use this when**: You want clean removal of expired companies from the system

#### 2. **Archive Mode** (Optional - For Audit Trails)
- The company's database is deleted from the server
- The Company entry is preserved in the main database but marked as deleted:
  - `db_created = False`
  - `db_name = None`
- The Company record remains for historical/audit purposes
- **Use this when**: You need to maintain audit records of deleted companies

## Implementation Details

### Modified Files

#### 1. `Lyraerp/scheduler.py`
**Function**: `delete_expired_trial_databases_job(dry_run=False, remove_company_entry=True)`

**Changes**:
- Added `remove_company_entry` parameter (default: `True`)
- When `remove_company_entry=True`: Completely deletes the Company record
- When `remove_company_entry=False`: Archives the record (original behavior)
- Enhanced logging for better tracking

**Example Usage**:
```python
# Complete removal (recommended)
delete_expired_trial_databases_job(remove_company_entry=True)

# Archive mode
delete_expired_trial_databases_job(remove_company_entry=False)

# Dry run (preview without deletion)
delete_expired_trial_databases_job(dry_run=True, remove_company_entry=True)
```

#### 2. `Lyraerp/management/commands/delete_expired_trial_databases.py`
**Command**: `python manage.py delete_expired_trial_databases`

**New Parameters**:
- `--dry-run`: Preview eligible companies without deletion
- `--keep-entries`: Archive mode (keep Company entries as deleted records)

**Example Usage**:
```bash
# Complete removal (default behavior)
python manage.py delete_expired_trial_databases

# Preview what will be deleted
python manage.py delete_expired_trial_databases --dry-run

# Archive mode (keep Company entries)
python manage.py delete_expired_trial_databases --keep-entries

# Preview with archive mode
python manage.py delete_expired_trial_databases --dry-run --keep-entries
```

## Usage Scenarios

### Scenario 1: Regular Scheduled Cleanup (Recommended)
```bash
# Run daily via cron/scheduler
python manage.py delete_expired_trial_databases
```
**Outcome**: Expired companies and their databases are completely removed after 7 days

### Scenario 2: With Audit Trail Preservation
```bash
# Run daily via cron/scheduler with archive mode
python manage.py delete_expired_trial_databases --keep-entries
```
**Outcome**: Databases are deleted, but Company records remain for audit purposes

### Scenario 3: Manual Verification Before Cleanup
```bash
# Check what will be deleted
python manage.py delete_expired_trial_databases --dry-run

# If satisfied, execute
python manage.py delete_expired_trial_databases
```

## Scheduler Integration

The scheduler job `_run_all_jobs()` calls this function as **JOB 5** with default parameters:
```python
def _run_all_jobs():
    logger.info("[SCHEDULER] Running all jobs...")
    # ... other jobs ...
    delete_expired_trial_databases_job()  # Uses default: remove_company_entry=True
    # ... other jobs ...
```

### To Change Default Behavior
Edit `Lyraerp/scheduler.py` in the `_run_all_jobs()` function:

**For archive mode**:
```python
delete_expired_trial_databases_job(remove_company_entry=False)
```

## Database Changes Required

If using **complete removal mode**, ensure your Company model has proper cascade deletes configured for related models:

```python
# In models that reference Company
class SomeModel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
```

Current setup uses:
- `models.CASCADE`: Automatically deletes related records when Company is deleted

## Logging and Monitoring

All operations are logged with detailed information:

```
✓ Complete Removal:
[SCHEDULER] JOB 5 - Completely removed database and Company entry 'ClientName' (xyz_2026) after license expiry

✗ Archive Mode:
[SCHEDULER] JOB 5 - Deleted license database 'xyz_2026' for 'ClientName' (Company entry archived)

✗ Errors:
[SCHEDULER] JOB 5 - Failed to remove Company entry for 'ClientName': <error details>
```

## Safety Features

1. **Grace Period**: 7-day grace period before deletion allows companies to renew
2. **Dry Run Mode**: Preview what will be deleted without making changes
3. **License Check**: Companies with valid active licenses are never deleted
4. **Error Handling**: Detailed error logging for troubleshooting
5. **Connection Cleanup**: Database connections are properly closed before deletion

## Rollback Strategy

### If You Need to Recover Deleted Companies

**With Archive Mode** (easier recovery):
```python
# Restore archived company
from company.models import Company
company = Company.objects.filter(db_created=False, db_name=None).first()
# Recreate database and update Company entry if needed
```

**With Complete Removal Mode** (requires backup):
```bash
# Restore from database backup
mysql -u root -p < /path/to/backup/company_db.sql
# Update Company entry in main database if needed
```

## Performance Considerations

- Deleting a Company with cascade deletes may take time if it has many related records
- Consider running this job during low-traffic hours
- Monitor error logs for cascade delete failures
- Large deletions might temporarily impact database performance

## Configuration Options

### Environment Variables (Optional)
You could extend the code to use environment variables:
```python
# In settings or .env
KEEP_DELETED_COMPANY_RECORDS = False  # or True for archive mode
```

### Change Default Behavior
Edit line in `Lyraerp/scheduler.py`:
```python
# Change this default
delete_expired_trial_databases_job(remove_company_entry=True)  # Default behavior

# To this for archive mode
delete_expired_trial_databases_job(remove_company_entry=False)
```

## FAQ

**Q: Can I switch between modes?**
A: Yes, use the `--keep-entries` flag or `remove_company_entry` parameter

**Q: What happens to user accounts?**
A: With CASCADE deletes, all users in that company are also deleted

**Q: How do I recover a deleted company?**
A: Restore from backup. Keep backups of your database

**Q: Is data immediately deleted?**
A: Yes, when deletion runs. Before that, there's a 7-day grace period

**Q: Can I extend the grace period?**
A: Yes, modify line in scheduler.py: `now.date() < expiry_date + timedelta(days=7)` to change 7 to desired days

## Support

For issues or questions:
1. Check logs: `/logs/django.log` or scheduler logs
2. Run with `--dry-run` to verify behavior
3. Review error messages for specific failures
