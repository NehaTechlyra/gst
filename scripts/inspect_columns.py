import os
import sys
import django
# Ensure project root is on sys.path so Django settings import works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()
from django.db import connection

def cols(table):
    with connection.cursor() as cur:
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", [table])
        return [r[0] for r in cur.fetchall()]

print('email_templates:', cols('email_templates_emailtemplatestyle'))
print('email_config:', cols('email_config_emailconfiguration'))
print('sms_config:', cols('sms_config_smsconfiguration'))
print('sms_templates:', cols('sms_templates_smstemplateoption'))
