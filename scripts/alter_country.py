import os
import sys
import django

# Ensure project root is on sys.path so Django package can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')

django.setup()

from django.db import connection

SQL = """
ALTER TABLE `Purchase_vendor`
MODIFY `country` varchar(100) NOT NULL DEFAULT '';
"""

try:
    with connection.cursor() as cur:
        cur.execute(SQL)
    print('ALTER TABLE executed successfully')
except Exception as e:
    print('Error executing ALTER TABLE:', e)
    raise
