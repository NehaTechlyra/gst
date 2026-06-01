
import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()

from company.models import Company

def list_sony_companies():
    print("Searching for companies named 'Sony' in MASTER database...")
    companies = Company.objects.using('default').filter(name__icontains='Sony')
    print(f"Found {len(companies)} matching record(s).\n")
    
    for c in companies:
        print(f"ID: {c.id}")
        print(f"Name: {c.name}")
        print(f"Created At: {c.created_at}")
        print(f"Trial Active: {c.trial_active}")
        print(f"Trial Expires: {c.trial_expires_at}")
        print(f"Is Trial Expired: {c.is_trial_expired}")
        print(f"DB Name: {c.db_name}")
        print("-" * 30)

if __name__ == "__main__":
    list_sony_companies()
