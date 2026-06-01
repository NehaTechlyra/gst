import os
import sys
import django
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()
from django.db import connection
with connection.cursor() as cur:
    cur.execute("SHOW COLUMNS FROM Purchase_contactperson")
    for r in cur.fetchall():
        print(r)
