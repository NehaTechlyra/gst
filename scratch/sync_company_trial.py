
import os
import django
import sys
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()

from company.models import Company

def sync_trial_status(company_id):
    print(f"Syncing Company ID: {company_id} in MASTER database...")
    
    try:
        # Fetch from master
        company = Company.objects.using('default').get(id=company_id)
        
        # New values based on user's confirmation and tenant DB dump
        # trial_expires_at: '2026-04-17 09:36:07.621012'
        # trial_created_at: '2026-04-01 09:36:07.607937'
        # trial_started_at: '2026-04-14 09:36:07.621012'
        # is_trial_expired: '1'
        # trial_active: '0'
        
        expires_at = datetime.strptime('2026-04-17 09:36:07.621012', '%Y-%m-%d %H:%M:%S.%f')
        created_at = datetime.strptime('2026-04-01 09:36:07.607937', '%Y-%m-%d %H:%M:%S.%f')
        started_at = datetime.strptime('2026-04-14 09:36:07.621012', '%Y-%m-%d %H:%M:%S.%f')
        
        # Make them timezone aware
        expires_at = timezone.make_aware(expires_at, dt_timezone.utc)
        created_at = timezone.make_aware(created_at, dt_timezone.utc)
        started_at = timezone.make_aware(started_at, dt_timezone.utc)

        # Update fields
        company.trial_active = False
        company.is_trial_expired = 1
        company.trial_expires_at = expires_at
        company.trial_created_at = created_at
        company.trial_started_at = started_at
        
        company.save(using='default', update_fields=[
            'trial_active', 
            'is_trial_expired', 
            'trial_expires_at', 
            'trial_created_at',
            'trial_started_at'
        ])
        
        print(f"Successfully synced master DB for '{company.name}' (ID: {company_id})")
        
        # Also check if it's already expired according to logic
        expired = company.check_trial_expired()
        print(f"check_trial_expired() result: {expired}")
        
    except Company.DoesNotExist:
        print(f"Error: Company ID {company_id} not found in master database.")
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    sync_trial_status(3)
