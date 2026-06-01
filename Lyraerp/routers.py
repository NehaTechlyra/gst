import logging
from django.core.exceptions import ImproperlyConfigured
from Lyraerp.utils.thread_locals import get_current_db

logger = logging.getLogger(__name__)

class CompanyDatabaseRouter:
    """Multi-tenant database router with user app in both databases"""
    
    MASTER_APPS = [
        "admin",
        "sessions",
        "messages",
        "staticfiles",
    ]
    
    DUAL_APPS = [
        "auth",
        "company",
        "contenttypes",
        "website",
        "user",
    ]
    
    ERP_APPS = [
        "Project", "Employee", "UserReq", "Purchase", "Tax", "Items", "PayTerms", "HR",
        "customer", "brand", "unit", "chart_of_accounts", "warehouse", "stock",
        "sales", "department", "designation", "leaves", "bank", "allowances", "journal",
        "expenses", "personaldocuments", "system_settings", "email_config", "sms_config",
        "crm", "sms_templates", "email_templates", "activity_log", "company_settings",
        "category", "type",
        "currencies","pricelist",
    ]
    
    def db_for_read(self, model, **hints):
        """Determine which database to read from"""
        app_label = model._meta.app_label
        
        # Master apps always use default
        if app_label in self.MASTER_APPS:
            return "default"
        
        # Dual apps (including user) prefer company DB if available
        if app_label in self.DUAL_APPS:
            # Check for explicit using hint first
            using = hints.get("using")
            if using:
                logger.debug(f"[READ] {app_label} → {using} (explicit)")
                return using
            
            # ✅ Use thread-local to get current company DB
            company_db = get_current_db()
            if company_db != "default":
                logger.debug(f"[READ] {app_label} → {company_db} (from thread-local)")
                return company_db
            
            # Fallback to master DB
            logger.debug(f"[READ] {app_label} → default (no context)")
            return "default"
        
        # ✅ ERP apps: Use thread-local to get company DB
        if app_label in self.ERP_APPS:
            # Check for explicit using hint first
            using = hints.get("using")
            if using and using != "default":
                logger.debug(f"[READ] {app_label} → {using} (explicit)")
                return using
            
            # ✅ Get from thread-local (set by middleware)
            company_db = get_current_db()
            
            if company_db != "default":
                logger.debug(f"[READ] {app_label} → {company_db} (from thread-local)")
                return company_db
            
            # ⚠️ No company context - return default but log warning
            logger.warning(
                f"[READ] {app_label} attempted without company context - "
                f"falling back to 'default' (may return empty results)"
            )
            return "default"
        
        return "default"
    
    def db_for_write(self, model, **hints):
        """Determine which database to write to"""
        app_label = model._meta.app_label
        
        # Master apps always use default
        if app_label in self.MASTER_APPS:
            return "default"
        
        # Dual apps (including user) prefer company DB if available
        if app_label in self.DUAL_APPS:
            # Explicit using takes precedence
            using = hints.get("using")
            if using:
                logger.debug(f"[WRITE] {app_label} → {using} (explicit)")
                return using
            
            # ✅ Use thread-local
            company_db = get_current_db()
            if company_db != "default":
                logger.debug(f"[WRITE] {app_label} → {company_db} (from thread-local)")
                return company_db
            
            # Fallback to master DB (this is OK for dual apps)
            logger.debug(f"[WRITE] {app_label} → default (no context)")
            return "default"
        
        # ERP apps MUST NOT write to default
        if app_label in self.ERP_APPS:
            # Check for explicit using hint first
            using = hints.get("using")
            if using:
                if using == "default":
                    logger.error(
                        f"❌ [WRITE] Blocked {app_label} write to 'default' database! "
                        f"Model: {model.__name__}"
                    )
                    raise ImproperlyConfigured(
                        f"Cannot save {app_label}.{model.__name__} to master database. "
                        f"A company database context is required."
                    )
                logger.debug(f"[WRITE] {app_label} → {using} (explicit)")
                return using
            
            # ✅ Check thread-local
            company_db = get_current_db()
            if company_db != "default":
                logger.debug(f"[WRITE] {app_label} → {company_db} (from thread-local)")
                return company_db
            
            # Check if instance already has a database set
            instance = hints.get("instance")
            if instance and hasattr(instance, "_state") and instance._state.db:
                db = instance._state.db
                if db == "default":
                    logger.error(
                        f"❌ [WRITE] Blocked {app_label}.{model.__name__} - "
                        f"instance._state.db is 'default'"
                    )
                    raise ImproperlyConfigured(
                        f"Cannot save {app_label}.{model.__name__} to master database. "
                        f"A company database context is required."
                    )
                logger.debug(f"[WRITE] {app_label} → {db} (from instance._state.db)")
                return db
            
            # CRITICAL: Block writes without any database context
            logger.error(
                f"❌ [WRITE] Blocked {app_label}.{model.__name__} - "
                f"No company database context available!"
            )
            raise ImproperlyConfigured(
                f"Cannot save {app_label}.{model.__name__} without company context. "
                f"Ensure request.company_db is set or use .using('company_db_name')"
            )
        
        return "default"
    
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations within same database"""
        # Same database → always allow
        if obj1._state.db and obj2._state.db and obj1._state.db == obj2._state.db:
            return True
        
        app1 = obj1._meta.app_label
        app2 = obj2._meta.app_label
        
        # Same category → allow
        if app1 in self.MASTER_APPS and app2 in self.MASTER_APPS:
            return True
        if app1 in self.DUAL_APPS and app2 in self.DUAL_APPS:
            return True
        if app1 in self.ERP_APPS and app2 in self.ERP_APPS:
            return True
        
        # Company app can relate to anything (it's the link)
        if app1 == "company" or app2 == "company":
            return True
        
        # Allow dual apps to relate to ERP apps (user → customer, etc.)
        if app1 in self.DUAL_APPS and app2 in self.ERP_APPS:
            return True
        if app1 in self.ERP_APPS and app2 in self.DUAL_APPS:
            return True
        
        return False
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Control which apps migrate to which databases"""
        
        # Master-only apps → ONLY on default
        if app_label in self.MASTER_APPS:
            result = db == "default"
            logger.info(f"[MIGRATE] {app_label} on {db}: {result} (MASTER_APPS)")
            return result
        
        # Dual apps (including user) → on ALL databases
        if app_label in self.DUAL_APPS:
            logger.info(f"[MIGRATE] {app_label} on {db}: True (DUAL_APPS)")
            return True
        
        # ERP apps → NEVER on default, ONLY on company databases
        if app_label in self.ERP_APPS:
            if db == "default":
                logger.warning(f"[MIGRATE] ❌ BLOCKING {app_label} from {db} (ERP_APPS)")
                return False
            else:
                logger.info(f"[MIGRATE] ✅ ALLOWING {app_label} on {db} (ERP_APPS)")
                return True
        
        # Unknown apps → only on default
        result = db == "default"
        logger.info(f"[MIGRATE] {app_label} on {db}: {result} (UNKNOWN)")
        return result