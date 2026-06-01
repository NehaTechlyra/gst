import os
import sys
import django
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()
from django.db import connection

SQL = '''
ALTER TABLE `Purchase_contactperson`
ADD COLUMN IF NOT EXISTS `created_at` DATETIME NULL,
ADD COLUMN IF NOT EXISTS `updated_at` DATETIME NULL;
'''

# Note: MySQL's ALTER TABLE ... ADD COLUMN IF NOT EXISTS is supported in newer versions.
# If your MySQL version doesn't support IF NOT EXISTS, the script will still work if you
# remove the IF NOT EXISTS or catch the exception below.

try:
    with connection.cursor() as cur:
        cur.execute(SQL)
    print('Columns added (or already present).')
except Exception as e:
    # Try a fallback: add without IF NOT EXISTS and ignore duplicate errors
    print('Primary attempt failed, trying fallback without IF NOT EXISTS:', e)
    SQL2 = '''
    ALTER TABLE `Purchase_contactperson`
    ADD COLUMN `created_at` DATETIME NULL,
    ADD COLUMN `updated_at` DATETIME NULL;
    '''
    try:
        with connection.cursor() as cur:
            cur.execute(SQL2)
        print('Fallback: Columns added.')
    except Exception as e2:
        print('Fallback also failed:', e2)
        raise
