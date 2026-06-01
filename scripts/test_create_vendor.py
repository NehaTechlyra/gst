import os
import sys
import django
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()
from Purchase.models import Vendor

try:
    v = Vendor.objects.create(
        vendor_code='TST001',
        vendor_type='company',
        company_name='Test Vendor',
        email='test_vendor_unique_001@example.com',
        country='United Kingdom',
    )
    print('Created vendor id:', v.id)
except Exception as e:
    print('Error creating vendor:', type(e), e)
    raise
