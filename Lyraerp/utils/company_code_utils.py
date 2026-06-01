"""
Simple Company Code Generator
Generates readable company codes in format: COMPANYNAME-YEAR

Examples:
- Tech Solutions → TECHSOLUTIONS-2025
- ABC Corp → ABCCORP-2025
- My Business → MYBUSINESS-2025
"""

import re
from datetime import datetime
from django.utils.text import slugify


def generate_company_code(company_name):
    """
    Generate a simple, readable company code.
    
    Format: COMPANYNAME-YEAR
    
    Args:
        company_name (str): The company name
        
    Returns:
        str: Generated company code (e.g., "TECHSOLUTIONS-2025")
        
    Examples:
        >>> generate_company_code("Tech Solutions")
        'TECHSOLUTIONS-2025'
        >>> generate_company_code("ABC Corp & Associates")
        'ABCCORP-2025'
    """
    # Get current year
    year = datetime.now().year
    
    # Clean company name:
    # 1. Remove special characters
    # 2. Remove spaces
    # 3. Convert to uppercase
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name)
    clean_name = clean_name.upper()
    
    # Limit to first 15 characters for readability
    clean_name = clean_name[:15]
    
    # Generate base code
    base_code = f"{clean_name}-{year}"
    
    return base_code


def generate_unique_company_code(company_name, check_exists_func=None):
    """
    Generate a unique company code with collision handling.
    
    If code exists, adds a number suffix: TECHSOLUTIONS-2025-2
    
    Args:
        company_name (str): The company name
        check_exists_func (callable): Function to check if code exists
            Should return True if code exists, False otherwise
            
    Returns:
        str: Unique company code
        
    Example:
        >>> def check_exists(code):
        ...     return code in ['TECHSOLUTIONS-2025']
        >>> generate_unique_company_code("Tech Solutions", check_exists)
        'TECHSOLUTIONS-2025-2'
    """
    base_code = generate_company_code(company_name)
    
    # If no check function provided, return base code
    if check_exists_func is None:
        return base_code
    
    # Check if base code is unique
    if not check_exists_func(base_code):
        return base_code
    
    # Add number suffix if code exists
    counter = 2
    while True:
        new_code = f"{base_code}-{counter}"
        if not check_exists_func(new_code):
            return new_code
        counter += 1
        
        # Safety limit
        if counter > 100:
            raise ValueError(f"Could not generate unique code for {company_name}")


def check_company_code_exists(code):
    """
    Check if a company code already exists in the database.
    
    Args:
        code (str): Company code to check
        
    Returns:
        bool: True if exists, False otherwise
    """
    from company.models import Company
    return Company.objects.using('default').filter(company_code=code).exists()


# ============================================================================
# DJANGO MODEL INTEGRATION
# ============================================================================

def auto_generate_company_code_on_save(sender, instance, **kwargs):
    """
    Signal handler to auto-generate company_code when creating a company.
    
    Add to your Company model signals:
    
    ```python
    from django.db.models.signals import pre_save
    from django.dispatch import receiver
    from company.models import Company
    from .utils.company_code_utils import auto_generate_company_code_on_save
    
    @receiver(pre_save, sender=Company)
    def generate_code(sender, instance, **kwargs):
        auto_generate_company_code_on_save(sender, instance, **kwargs)
    ```
    """
    # Only generate for new companies (no ID yet)
    if not instance.pk and not instance.company_code:
        instance.company_code = generate_unique_company_code(
            instance.name,
            check_company_code_exists
        )


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Manual generation in a view
---------------------------------------

from company.utils.company_code_utils import generate_unique_company_code, check_company_code_exists

def create_company(request):
    company_name = request.POST.get('name')
    
    # Generate unique code
    company_code = generate_unique_company_code(
        company_name,
        check_company_code_exists
    )
    
    # Create company
    company = Company.objects.create(
        name=company_name,
        company_code=company_code,
        # ... other fields
    )
    
    return company


EXAMPLE 2: Auto-generation in model save()
-------------------------------------------

class Company(models.Model):
    name = models.CharField(max_length=255)
    company_code = models.CharField(max_length=20, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate code if not set
        if not self.company_code:
            from .utils.company_code_utils import generate_unique_company_code, check_company_code_exists
            self.company_code = generate_unique_company_code(
                self.name,
                check_company_code_exists
            )
        
        super().save(*args, **kwargs)


EXAMPLE 3: Using Django signals (RECOMMENDED)
----------------------------------------------

# In company/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from company.models import Company
from .utils.company_code_utils import auto_generate_company_code_on_save

@receiver(pre_save, sender=Company)
def generate_company_code(sender, instance, **kwargs):
    auto_generate_company_code_on_save(sender, instance, **kwargs)

# In company/__init__.py
default_app_config = 'company.apps.CompanyConfig'

# In company/apps.py
from django.apps import AppConfig

class CompanyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'company'
    
    def ready(self):
        import company.signals
"""


# ============================================================================
# TEST CASES
# ============================================================================

def test_company_code_generation():
    """Test the company code generation."""
    test_cases = [
        ("Tech Solutions", "TECHSOLUTIONS-2025"),
        ("ABC Corp", "ABCCORP-2025"),
        ("My Business & Co.", "MYBUSINESS-2025"),
        ("123 Numbers", "123NUMBERS-2025"),
        ("Very Long Company Name That Should Be Truncated", "VERYLONGCOMPANY-2025"),
    ]
    
    year = datetime.now().year
    
    for company_name, expected_pattern in test_cases:
        code = generate_company_code(company_name)
        print(f"✓ {company_name} → {code}")
        assert str(year) in code, f"Year {year} not in {code}"
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_company_code_generation()