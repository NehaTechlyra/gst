# Lyraerp/utils/license_utils.py

"""
License key utilities for module access control
"""
import logging
from typing import List, Optional, Dict
import json
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_license_key(license_key_str: str) -> dict:
    """
    Parse license key and extract module permissions
    
    Args:
        license_key_str: Encoded license key string
        
    Returns:
        Dictionary with license information
    """
    if not license_key_str:
        logger.warning("No license key provided")
        return {
            'modules': None,  # None = full access by default
            'expiry_date': None,
            'max_users': 10,
            'company_name': None,
            'is_valid': True,
            'is_expired': False
        }
    
    try:
        # Decode base64 encoded JSON license
        decoded = base64.b64decode(license_key_str).decode('utf-8')
        license_data = json.loads(decoded)
        
        expiry_date = license_data.get('expiry_date')
        
        return {
            'modules': license_data.get('modules', None),  # None = all modules
            'expiry_date': expiry_date,
            'max_users': license_data.get('max_users', 10),
            'company_name': license_data.get('company_name'),
            'is_valid': True,  # Validity is now determined by is_license_expired field in DB
            'license_type': license_data.get('license_type', 'standard'),
            'is_expired': False  # This will be checked against DB is_license_expired flag
        }
        
    except Exception as e:
        logger.error(f"Failed to parse license key: {e}")
        # Default to full access on parse error
        return {
            'modules': None,
            'expiry_date': None,
            'max_users': 10,
            'company_name': None,
            'is_valid': True,
            'is_expired': False
        }


def get_allowed_modules_from_license(company_id: int, using: str = 'default') -> Optional[List[str]]:
    """
    Extract allowed module categories from license key using DB field.
    
    Args:
        company_id: ID of the company
        using: Database alias to use (for multi-tenant)
        
    Returns:
        List of allowed module categories (e.g., ['Sales', 'CRM', 'HR'])
        Returns None for full license (all modules enabled)
        Returns [] if license is expired or no license
    """
    try:
        from company_settings.models import LicenseKey
        
        # Try to get company's license
        license_obj = LicenseKey.objects.using(using).get(company_id=company_id)
        
        # Check the is_license_expired flag (set by scheduled task at midnight)
        if license_obj.is_license_expired:
            logger.warning(f"License for company {company_id} is expired, restricting access")
            return []  # Empty list = no modules
        
        # Parse the license key to get module list
        license_data = parse_license_key(license_obj.license_key)
        modules = license_data.get('modules', None)
        
        if modules is None:
            logger.info(f"Full license detected for company {company_id}, enabling all modules")
            return None  # None = all modules
        
        logger.info(f"License for company {company_id} allows modules: {modules}")
        return modules
        
    except LicenseKey.DoesNotExist:
        logger.info(f"No license for company {company_id}, enabling all modules")
        return None
    except Exception as e:
        logger.error(f"Error getting allowed modules for company {company_id}: {e}")
        # Fail open - allow all modules on error
        return None


def check_module_access(license_key: str, module_category: str) -> bool:
    """
    Check if a specific module category is allowed by the license
    
    Args:
        license_key: Company's license key
        module_category: Category to check (e.g., 'Sales', 'CRM', 'HR')
        
    Returns:
        True if module is allowed, False otherwise
    """
    allowed_modules = get_allowed_modules_from_license(license_key)
    
    # None means full license - all modules allowed
    if allowed_modules is None:
        return True
    
    # Check if module category is in allowed list
    return module_category in allowed_modules


def get_module_category(module_name: str) -> str:
    """
    Extract category from full module name and map to license module codes
    
    Args:
        module_name: Full module name (e.g., 'Sales Quotation', 'CRM Lead', 'HR Dashboard')
        
    Returns:
        License module code (e.g., 'SALES_PURCHASE', 'HR', 'REPORTS')
    """
    module_lower = module_name.lower()
    
    # ✅ COMPREHENSIVE MAPPING TO LICENSE CODES
    
    # HR Module
    if any(keyword in module_lower for keyword in ['hr', 'employee', 'recruitment', 'department', 'designation', 'allowance', 'leave']):
        return 'HR'
    
    # Sales & Purchase Module
    if any(keyword in module_lower for keyword in ['sales', 'purchase', 'quotation', 'order', 'invoice', 'bill', 'payment', 'delivery', 'customer', 'vendor', 'brand']):
        return 'SALES_PURCHASE'
    
    # CRM Module (if you have separate CRM license code, otherwise map to SALES_PURCHASE)
    if any(keyword in module_lower for keyword in ['crm', 'lead', 'opportunity', 'presale', 'follow']):
        return 'SALES_PURCHASE'  # Or 'CRM' if you have separate license
    
    # Accounts/Finance Module
    if any(keyword in module_lower for keyword in ['account', 'journal', 'chart', 'finance', 'bank', 'expense', 'tax', 'payterm']):
        return 'FINANCE'
    
    # Reports Module
    if any(keyword in module_lower for keyword in ['report', 'trial balance', 'balance sheet', 'profit', 'loss']):
        return 'REPORTS'
    
    # Inventory Module
    if any(keyword in module_lower for keyword in ['item', 'inventory', 'warehouse', 'stock', 'unit']):
        return 'INVENTORY'
    
    # User Management Module (Masters)
    if any(keyword in module_lower for keyword in ['user', 'role', 'permission', 'masters']):
        return 'USER_MGMT'
    
    # Communication Module
    if any(keyword in module_lower for keyword in ['email', 'sms', 'template', 'notification']):
        return 'COMMUNICATION'
    
    # System Settings
    if any(keyword in module_lower for keyword in ['system', 'setting', 'company', 'configuration']):
        return 'SYSTEM'
    
    # Default: Try to extract first word as category
    first_word = module_name.split()[0] if module_name else 'Unknown'
    logger.warning(f"Unknown module category for '{module_name}', defaulting to '{first_word}'")
    return first_word.upper()


# Example license key generators remain the same...
def generate_trial_license(company_name: str, modules: List[str]) -> str:
    """Generate a trial license key"""
    from datetime import datetime, timedelta
    
    license_data = {
        'company_name': company_name,
        'modules': modules,
        'expiry_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'max_users': 5,
        'license_type': 'trial'
    }
    
    json_str = json.dumps(license_data)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    return encoded


def generate_full_license(company_name: str, max_users: int = 100, years: int = 1) -> str:
    """Generate a full license key with all modules"""
    from datetime import datetime, timedelta
    
    license_data = {
        'company_name': company_name,
        'modules': None,  # None = all modules
        'expiry_date': (datetime.now() + timedelta(days=365*years)).strftime('%Y-%m-%d'),
        'max_users': max_users,
        'license_type': 'full'
    }
    
    json_str = json.dumps(license_data)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    return encoded


def generate_custom_license(
    company_name: str, 
    modules: List[str], 
    max_users: int = 50,
    years: int = 1
) -> str:
    """Generate a custom license key with specific modules"""
    from datetime import datetime, timedelta
    
    license_data = {
        'company_name': company_name,
        'modules': modules,
        'expiry_date': (datetime.now() + timedelta(days=365*years)).strftime('%Y-%m-%d'),
        'max_users': max_users,
        'license_type': 'custom'
    }
    
    json_str = json.dumps(license_data)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    return encoded