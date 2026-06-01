import os
import sys
import django
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')

django.setup()
from django.db import connection

old_cols = ['crtd_at','crtd_by_id','updt_at','updt_by_id']
# Find which of these columns exist
existing = []
with connection.cursor() as cur:
    cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", ['Purchase_vendor'])
    cols = [r[0] for r in cur.fetchall()]
    for c in old_cols:
        if c in cols:
            existing.append(c)

if not existing:
    print('No legacy columns found; nothing to do.')
else:
    # Drop any foreign key constraints that reference these columns first
    with connection.cursor() as cur:
        cur.execute(
            "SELECT CONSTRAINT_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Purchase_vendor' AND REFERENCED_TABLE_NAME IS NOT NULL"
        )
        rows = cur.fetchall()
        fks = [(r[0], r[1]) for r in rows if r[1] in existing]

    # fks may be empty; drop constraints first
    if fks:
        with connection.cursor() as cur:
            for fk_name, col_name in fks:
                try:
                    cur.execute(f"ALTER TABLE `Purchase_vendor` DROP FOREIGN KEY `{fk_name}`")
                    print('Dropped foreign key', fk_name, 'for column', col_name)
                except Exception as e:
                    print('Error dropping FK', fk_name, ':', e)
                    raise

    # Now drop the existing columns
    sql = 'ALTER TABLE `Purchase_vendor` ' + ', '.join([f'DROP COLUMN `{c}`' for c in existing])
    try:
        with connection.cursor() as cur:
            cur.execute(sql)
        print('Dropped columns:', existing)
    except Exception as e:
        print('Error dropping columns:', e)
        raise
