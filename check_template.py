import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')
django.setup()

from email_templates.models import EmailTemplate, EmailTemplateStyle

print("=== Checking Quotation Details Template ===")
styles = EmailTemplateStyle.objects.filter(email_template__name='Quotation Details')
print(f"Found {styles.count()} template style(s)")

for s in styles:
    print(f"\nStyle: {s.style}")
    print(f"Default: {s.is_default}")
    print(f"Status: {s.status}")
    print(f"Subject: {s.subject}")
    print(f"Body (first 100 chars): {s.body[:100] if s.body else 'EMPTY'}")

print("\n=== All Email Templates ===")
templates = EmailTemplate.objects.all()
for t in templates:
    print(f"Template: {t.name}, Status: {t.status}")
    styles = EmailTemplateStyle.objects.filter(email_template=t)
    for st in styles:
        print(f"  - Style: {st.style}, Default: {st.is_default}, Status: {st.status}")
