# Database Cleanup Configuration
# This file contains configuration options for the database cleanup feature

# ============================================================================
# CLEANUP MODE CONFIGURATION
# ============================================================================
# Default behavior: True = Complete removal, False = Archive mode
DEFAULT_REMOVE_EXPIRED_COMPANY_ENTRIES = True

# Grace period in days (time between expiry and deletion)
CLEANUP_GRACE_PERIOD_DAYS = 7

# Enable/disable the automatic cleanup job
ENABLE_AUTOMATIC_CLEANUP = True

# ============================================================================
# DELETION WARNING EMAIL CONFIGURATION
# ============================================================================
# Maximum number of warning emails to send during grace period
MAX_DELETION_WARNING_EMAILS = 3

# Interval between warning emails in hours (48 = every 2 days)
DELETION_WARNING_EMAIL_INTERVAL_HOURS = 48

# ============================================================================
# LOGGING AND MONITORING
# ============================================================================
# Log level for cleanup operations
CLEANUP_LOG_LEVEL = 'WARNING'  # Options: DEBUG, INFO, WARNING, ERROR

# Send email notification to admins after cleanup
NOTIFY_ADMINS_AFTER_CLEANUP = True

# Admin email for cleanup notifications
CLEANUP_NOTIFICATION_EMAIL = 'admin@example.com'

# ============================================================================
# SAFETY FEATURES
# ============================================================================
# Require explicit confirmation before complete removal
REQUIRE_CONFIRMATION_FOR_COMPLETE_REMOVAL = False

# Create backup before deletion (if implemented)
CREATE_BACKUP_BEFORE_DELETION = True

# Backup location path
BACKUP_LOCATION = '/backups/deleted_companies/'

# ============================================================================
# ROLLBACK AND RECOVERY
# ============================================================================
# Days to keep recovery backups
BACKUP_RETENTION_DAYS = 30

# Allow recovery window (days to restore deleted company)
RECOVERY_WINDOW_DAYS = 30
