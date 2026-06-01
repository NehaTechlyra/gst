import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Lyraerp.settings')
django.setup()
from email_templates.models import EmailTemplate, EmailTemplateStyle

def show(name):
    styles = EmailTemplateStyle.objects.filter(email_template__name=name)
    print(f"=== {name} ({styles.count()} styles) ===")
    for s in styles:
        print('Style:', s.style)
        print('Default:', s.is_default)
        print('Status:', s.status)
        print('Subject:', repr(s.subject))
        body = s.body or ''
        print('Body (first 400 chars):')
        print(body[:400].replace('\n','\\n'))
        print('---')

show('Quatation Details')
show('Quotation Details')
show('Order Details')
show('Order')
show('Order Email')
