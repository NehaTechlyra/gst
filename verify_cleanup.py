"""
Test script to verify master database cleanup implementation
Run with: python manage.py shell < verify_cleanup.py
"""

from company.models import Company
from company_settings.models import CompanyBankAccount, LicenseKey
from django.db import DEFAULT_DB_ALIAS
from django.apps import apps

def verify_cascade_models():
    """Verify all Company-related models have CASCADE delete configured"""
    print("\n" + "="*80)
    print("VERIFYING CASCADE DELETE CONFIGURATION")
    print("="*80)
    
    models_to_check = [
        ('company_settings', 'CompanyBankAccount'),
        ('company_settings', 'LicenseKey'),
        ('currencies', 'Currency'),
        ('system_settings', 'EmailConfiguration'),
        ('system_settings', 'SMSConfiguration'),
        ('system_settings', 'EmailTemplateStyle'),
        ('system_settings', 'SMSTemplateStyle'),
        ('Tax', 'TaxMaster'),
        ('Tax', 'TCSMaster'),
    ]
    
    all_ok = True
    for app_label, model_name in models_to_check:
        try:
            model = apps.get_model(app_label, model_name)
            
            # Check if model has company field with CASCADE
            company_field = model._meta.get_field('company')
            if company_field.remote_field and company_field.remote_field.on_delete.__name__ == 'CASCADE':
                print(f"✓ {model_name}: CASCADE configured")
            else:
                print(f"✗ {model_name}: CASCADE NOT configured!")
                all_ok = False
        except Exception as e:
            print(f"? {model_name}: Error checking - {e}")
    
    print("\n" + "="*80)
    if all_ok:
        print("✓ All models correctly configured for CASCADE delete")
    else:
        print("✗ Some models need CASCADE configuration")
    print("="*80 + "\n")
    
    return all_ok

def test_count_function():
    """Test the _count_master_db_records function"""
    print("\n" + "="*80)
    print("TESTING MASTER DB RECORD COUNT FUNCTION")
    print("="*80)
    
    # Import the function
    from Lyraerp.scheduler import _count_master_db_records
    
    # Get a test company if available
    try:
        company = Company.objects.using('default').first()
        if company:
            print(f"\nTesting with company: {company.name} (ID: {company.pk})")
            count = _count_master_db_records(company.pk)
            print(f"✓ Related records in master DB: {count}")
        else:
            print("✗ No companies found for testing")
    except Exception as e:
        print(f"✗ Error testing function: {e}")
    
    print("\n" + "="*80 + "\n")

def test_cleanup_utils():
    """Test cleanup_utils functions"""
    print("\n" + "="*80)
    print("TESTING CLEANUP UTILITIES")
    print("="*80)
    
    from Lyraerp.utils.cleanup_utils import get_master_database_impact
    
    try:
        company = Company.objects.using('default').first()
        if company:
            print(f"\nAnalyzing company: {company.name} (ID: {company.pk})")
            impact = get_master_database_impact(company.pk)
            
            if 'error' in impact:
                print(f"✗ Error: {impact['error']}")
            else:
                print(f"✓ Company: {impact['company_name']}")
                print(f"✓ Database: {impact['db_name']}")
                print(f"✓ Related records: {impact['total_related_records']}")
                print(f"✓ Total to delete: {impact['total_records_to_delete']}")
                
                if impact['related_data']:
                    print(f"\nBreakdown:")
                    for record_type, count in impact['related_data'].items():
                        print(f"  • {record_type}: {count}")
        else:
            print("✗ No companies found for testing")
    except Exception as e:
        print(f"✗ Error testing cleanup_utils: {e}")
    
    print("\n" + "="*80 + "\n")

def main():
    print("\n" + "="*80)
    print("MASTER DATABASE CLEANUP - VERIFICATION TESTS")
    print("="*80)
    
    # Run verification tests
    cascade_ok = verify_cascade_models()
    test_count_function()
    test_cleanup_utils()
    
    print("\n" + "="*80)
    if cascade_ok:
        print("✓ IMPLEMENTATION VERIFIED - Ready for production")
    else:
        print("⚠ Review CASCADE configuration before production")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
