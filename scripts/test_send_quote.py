import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
import django
django.setup()
from django.test import RequestFactory
from sales.views import send_message
from django.contrib.auth.models import AnonymousUser
from django.core.mail.message import EmailMultiAlternatives

# Monkeypatch send to avoid real SMTP
orig_send = EmailMultiAlternatives.send

def fake_send(self, fail_silently=False):
    print('FAKE SEND called: subject=', self.subject)
    return 1

EmailMultiAlternatives.send = fake_send

rf = RequestFactory()
request = rf.post('/dummy')
request.user = AnonymousUser()
# add GET parameter
request.META['QUERY_STRING'] = 'method=email'

resp = send_message(request, 1)
print('Response:', resp.status_code, getattr(resp, 'content', None))

# restore
EmailMultiAlternatives.send = orig_send
