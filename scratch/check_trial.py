
import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()

from company.models import Company

def check_company(company_id):
    print(f"Checking Company ID: {company_id}")
    
    # Check default DB
    try:
        c_master = Company.objects.using('default').get(id=company_id)
        print("\n--- MASTER DATABASE (default) ---")
        print(f"Name: {c_master.name}")
        print(f"Trial Active: {c_master.trial_active}")
        print(f"Trial Started: {c_master.trial_started_at}")
        print(f"Trial Expires: {c_master.trial_expires_at}")
        print(f"Is Trial Expired (flag): {c_master.is_trial_expired}")
        print(f"Days until expires: {c_master.days_until_trial_expires()}")
    except Company.DoesNotExist:
        print("\n--- MASTER DATABASE ---")
        print("Record not found!")

    # Check tenant DB
    try:
        # Fetch again to get latest data including db_name
        c_master = Company.objects.using('default').get(id=company_id)
        if c_master.db_name:
            c_tenant = Company.objects.using(c_master.db_name).get(id=company_id)
            print(f"\n--- TENANT DATABASE ({c_master.db_name}) ---")
            print(f"Name: {c_tenant.name}")
            print(f"Trial Active: {c_tenant.trial_active}")
            print(f"Trial Started: {c_tenant.trial_started_at}")
            print(f"Trial Expires: {c_tenant.trial_expires_at}")
            print(f"Is Trial Expired (flag): {c_tenant.is_trial_expired}")
            print(f"Days until expires: {c_tenant.days_until_trial_expires()}")
        else:
            print(f"\n--- TENANT DATABASE ---")
            print("No db_name set for this company.")
    except Exception as e:
        print(f"\n--- TENANT DATABASE ---")
        print(f"Error accessing tenant DB: {e}")

if __name__ == "__main__":
    check_company(3)
