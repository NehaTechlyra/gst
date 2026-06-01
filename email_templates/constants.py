# email_templates/constants.py

TEMPLATE_NAME_CHOICES = [
    ("Document Expiry Reminder", "Document Expiry Reminder"),
    ("Document Expired Reminder", "Document Expired Reminder"),
    ("Appointment Letter", "Appointment Letter"),
    ("Invoice", "Invoice"),
    ("Performa Invoice", "Performa Invoice"),
    ("Quotation", "Quotation"),
    ("Payment Received", "Payment Received"),
    ("Payment Made", "Payment Made"),
    ("Order", "Order"),
    ("Bill", "Bill"),
]

# ── Shared inline-style snippets ──────────────────────────────────────────────
_STRIPE_PURPLE = "background-color:#55588b"
_STRIPE_RED    = "background-color:#c0392b"
_STRIPE_GREEN  = "background-color:#11998e"

def _email_wrap(stripe_color, logo_row, stripe_body, body_content, footer_text):
    """Build a fully inline, table-based email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="{stripe_color};padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        {stripe_body}
      </td></tr>
      <tr><td style="padding:36px 40px;">{body_content}</td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        {footer_text}
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def _pill(color, text):
    return f"""<table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
      <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;{text}</td>
    </tr></table>"""


def _details_card(title, rows):
    """rows = list of (label, value) tuples"""
    inner = ""
    for i, (label, value) in enumerate(rows):
        border = "" if i == len(rows)-1 else "border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;"
        inner += f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="{border}">
          <tr>
            <td style="font-size:14px;color:#6b6f9a;font-weight:500;">{label}</td>
            <td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">{value}</td>
          </tr></table>"""
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
      <tr><td style="padding:22px 24px;">
        <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">{title}</div>
        {inner}
      </td></tr></table>"""


def _info_card(title, body, color="#55588b", bg="#dce2f9"):
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{bg};border-radius:10px;margin-bottom:24px;">
      <tr><td style="padding:22px 24px;">
        <div style="font-size:17px;font-weight:700;color:{color};margin-bottom:10px;font-family:Georgia,serif;">{title}</div>
        <div style="font-size:14px;color:#3a3d6b;line-height:1.65;">{body}</div>
      </td></tr></table>"""


def _notice(icon, text, bg="#fffbeb", border="#fde68a", text_color="#7a5f00"):
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">
      <tr><td style="background:{bg};border:1px solid {border};border-radius:8px;padding:14px 16px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="font-size:18px;vertical-align:top;padding-right:10px;">{icon}</td>
          <td style="font-size:13px;color:{text_color};line-height:1.55;">{text}</td>
        </tr></table>
      </td></tr></table>"""


def _attachment_notice(label):
    return _notice("📎", f"<strong>{label} PDF Attached</strong> — Please find the complete details in the attached PDF file.")


def _amount_card(amount, sub_label, sub_value):
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;text-align:center;">
      <tr><td style="padding:28px;">
        <div style="font-size:12px;color:#6b6f9a;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Amount Due</div>
        <div style="font-size:38px;font-weight:700;color:#55588b;font-family:Georgia,serif;">{amount}</div>
        <div style="font-size:13px;color:#6b6f9a;margin-top:6px;">{sub_label}: {sub_value}</div>
      </td></tr></table>"""


def _footer(sig):
    return f'<p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">{sig}</p><p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>'


def _steps_card(title, steps, color="#c0392b", bg="#fdf0ef", border_color="#f5c6c2", text_color="#7a2020"):
    inner = ""
    for i, step in enumerate(steps, 1):
        inner += f"""<table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px;"><tr>
          <td style="background:{color};color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;">{i}</td>
          <td style="padding-left:12px;font-size:14px;color:{text_color};line-height:1.5;">{step}</td>
        </tr></table>"""
    return f"""<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{bg};border:1px solid {border_color};border-radius:10px;margin-bottom:24px;">
      <tr><td style="padding:22px 24px;">
        <div style="font-size:17px;font-weight:700;color:{color};margin-bottom:16px;font-family:Georgia,serif;">{title}</div>
        {inner}
      </td></tr></table>"""


# ── Hardcoded templates ───────────────────────────────────────────────────────

HARDCODED_EMAIL_TEMPLATES = {

    # ── Payment Received ───────────────────────────────────────────────────
    "Appointment Letter": [
        {
            "style": "Professional",
            "subject": "Appointment Letter - [[designation]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Appointment Letter</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Offer confirmation for [[designation]]</div>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[candidate]]</strong>,</p>
        <p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#444444;">We are pleased to appoint you as <strong>[[designation]]</strong> in the <strong>[[department]]</strong> department at <strong>[[company]]</strong>.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Offer Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Job Title</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[job_title]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">CTC</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[offered_ctc]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Joining Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[joining_date]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Reporting Manager</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[reporting_manager]]</td></tr>
            </table>
          </td></tr>
        </table>
        <p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#444444;">Please confirm your acceptance on or before <strong>[[expiry_date]]</strong>.</p>
        <p style="margin:0;font-size:15px;line-height:1.7;color:#444444;">Regards,<br><strong>[[company]]</strong></p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
        },
    ],

    "Payment Received": [
        {
            "style": "Professional",
            "subject": "Payment Received",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Payment Received</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Thank you for your payment</div>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[customer]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">We have received your payment. Below are the details for your reference.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:10px;font-family:Georgia,serif;">Payment Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Payment</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">&nbsp;</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 0;text-align:left;">
            <p style="margin:0;font-size:13px;color:#6b6f9a;">If you have any questions, reply to this email or contact our support team.</p>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Best regards, <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": False,
        },
        {
            "style": "Simple",
            "subject": "Payment Received",
            "body": "Dear [[customer]],\n\nWe have received your payment dated [[date]] for [[amount]]. Thank you.\n\n[[company]]",
            "is_hardcoded": True,
        },
    ],

    # ── Payment Made ───────────────────────────────────────────────────────
    "Payment Made": [
        {
            "style": "Professional",
            "subject": "Payment Made",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Payment Made</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Payment has been made to your account</div>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[vendor]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">We have processed a payment. Below are the details for your reference.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:10px;font-family:Georgia,serif;">Payment Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Payment</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">&nbsp;</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 0;text-align:left;">
            <p style="margin:0;font-size:13px;color:#6b6f9a;">If you have any questions, reply to this email or contact our support team.</p>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Best regards, <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": False,
        },
        {
            "style": "Simple",
            "subject": "Payment Made",
            "body": "Dear [[vendor]],\n\nWe have made a payment dated [[date]] for [[amount]]. Thank you.\n\n[[company]]",
            "is_hardcoded": True,
        },
    ],

    # ── Document Expiry Reminder ──────────────────────────────────────────────
    "Document Expiry Reminder": [
        {
            "style": "Professional",
            "subject": "Document Expiry Reminder - [[doc]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Document Expiry Reminder</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Action required before your document expires</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Expires on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">This is a friendly reminder that your <strong>[[doc]]</strong> will expire on <strong>[[date]]</strong>. Please ensure you renew it at your earliest convenience to avoid any disruptions.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:10px;font-family:Georgia,serif;">Document Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Document</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[doc]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Expiry Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">💡</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;">If you have already renewed this document, please disregard this message. Thank you for your attention to this matter.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Best regards, <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
        },
        {
            "style": "Friendly",
            "subject": "Hey! Your [[doc]] is expiring soon",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Quick Reminder! 👋</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Just a friendly nudge about your document</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Expires on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hi <strong>[[employee]]</strong>!</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Just a heads up — your <strong>[[doc]]</strong> is expiring on <strong>[[date]]</strong>. We know life gets busy, so we thought we'd give you a gentle nudge! 😊</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:20px 24px;">
            <div style="font-size:17px;font-weight:700;color:#92600a;margin-bottom:8px;font-family:Georgia,serif;">⏰ Don't forget to renew!</div>
            <div style="font-size:14px;color:#7a5f00;line-height:1.6;">Make sure to renew your <strong>[[doc]]</strong> before <strong>[[date]]</strong> to keep everything running smoothly.</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#dce2f9;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">✅</td>
              <td style="font-size:13px;color:#3a3d6b;line-height:1.55;">Already renewed? Awesome — you can safely ignore this message!</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Cheers, the <strong>[[company]]</strong> Team 🎉</p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
        },
    ],

    # ── Document Expired Reminder ─────────────────────────────────────────────
    "Document Expired Reminder": [
        {
            "style": "Professional",
            "subject": "URGENT: Your [[doc]] has expired",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#c0392b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Document Expired</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Immediate action is required</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Expired on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Your <strong>[[doc]]</strong> has expired on <strong>[[date]]</strong>. Please submit the renewed document immediately to ensure compliance and avoid disruptions to your work.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fdf0ef;border:1px solid #f5c6c2;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:20px 24px;">
            <div style="font-size:17px;font-weight:700;color:#c0392b;margin-bottom:8px;font-family:Georgia,serif;">⚠️ Urgent: Document Expired</div>
            <div style="font-size:14px;color:#7a2020;line-height:1.65;">Your <strong>[[doc]]</strong> is no longer valid. Please renew it as soon as possible and contact HR if you need assistance with the renewal process.</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#dce2f9;border-radius:8px;padding:14px 16px;font-size:14px;color:#3a3d6b;line-height:1.65;">
            This requires your <strong>immediate attention</strong>. Failure to renew may result in compliance issues.
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Best regards, <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
        },
        {
            "style": "Urgent",
            "subject": "⚠️ ACTION REQUIRED: [[doc]] Expired",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#c0392b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">🚨 Immediate Action Required</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Your document has expired — act now</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Expired on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Your <strong>[[doc]]</strong> expired on <strong>[[date]]</strong>. This document is critical for compliance. Please take the following steps immediately.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fdf0ef;border:1px solid #f5c6c2;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#c0392b;margin-bottom:16px;font-family:Georgia,serif;">What you need to do:</div>
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px;"><tr>
              <td style="background:#c0392b;color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;">1</td>
              <td style="padding-left:12px;font-size:14px;color:#7a2020;line-height:1.5;">Renew your <strong>[[doc]]</strong> as soon as possible</td>
            </tr></table>
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px;"><tr>
              <td style="background:#c0392b;color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;">2</td>
              <td style="padding-left:12px;font-size:14px;color:#7a2020;line-height:1.5;">Submit the updated document to HR</td>
            </tr></table>
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="background:#c0392b;color:#fff;border-radius:50%;width:24px;height:24px;text-align:center;vertical-align:middle;font-size:12px;font-weight:700;">3</td>
              <td style="padding-left:12px;font-size:14px;color:#7a2020;line-height:1.5;">Confirm receipt with your manager</td>
            </tr></table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fdf0ef;border:1px solid #f5c6c2;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">⚠️</td>
              <td style="font-size:13px;color:#7a2020;line-height:1.55;">Failure to comply may result in disciplinary action. Please act immediately.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">HR Department — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
        },
    ],

    # ── Invoice ───────────────────────────────────────────────────────────────
    "Invoice": [
        {
            "style": "Professional",
            "subject": "Invoice from [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Invoice</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Please find your invoice details below</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Due on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Please find your invoice details below. Payment can be made through the methods outlined in the attached PDF.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Invoice Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Due Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Invoice PDF Attached</strong> — Please find the complete invoice details in the attached PDF file.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you for your business — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
        {
            "style": "Modern",
            "subject": "Your Invoice #[[code]] - [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Invoice #[[code]]</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Your invoice is ready</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Due on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hi <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Your invoice is ready! Please review the details and process payment at your earliest convenience.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;text-align:center;">
          <tr><td style="padding:28px;">
            <div style="font-size:12px;color:#6b6f9a;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Amount Due</div>
            <div style="font-size:38px;font-weight:700;color:#55588b;font-family:Georgia,serif;">[[amount]]</div>
            <div style="font-size:13px;color:#6b6f9a;margin-top:6px;">Due by [[date]]</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Invoice PDF Attached</strong> — Check your attachments for the complete invoice details.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
    ],

    # ── Performa Invoice ─────────────────────────────────────────────────────
    "Performa Invoice": [
        {
            "style": "Professional",
            "subject": "Performa Invoice from [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Performa Invoice</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Please find your performa invoice details below</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Date [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Please find your performa invoice details below. The complete document is attached as a PDF.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Performa Invoice Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">&#128206;</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Performa Invoice PDF Attached</strong> &mdash; Please find the complete performa invoice details in the attached PDF file.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you for your business &mdash; <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">&copy; 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
        {
            "style": "Modern",
            "subject": "Your Performa Invoice #[[code]] - [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Performa Invoice #[[code]]</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Your performa invoice is ready</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Date [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hi <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Your performa invoice is ready. Please review the attached PDF for the complete details.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;text-align:center;">
          <tr><td style="padding:28px;">
            <div style="font-size:12px;color:#6b6f9a;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Performa Invoice Amount</div>
            <div style="font-size:38px;font-weight:700;color:#55588b;font-family:Georgia,serif;">[[amount]]</div>
            <div style="font-size:13px;color:#6b6f9a;margin-top:6px;">Dated [[date]]</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">&#128206;</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Performa Invoice PDF Attached</strong> &mdash; Check your attachments for the complete performa invoice details.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you &mdash; <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">&copy; 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
    ],

    # ── Quotation ─────────────────────────────────────────────────────────────
    "Quotation": [
        {
            "style": "Professional",
            "subject": "Quotation from [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Quotation</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Thank you for your interest</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Valid until [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Thank you for your interest. Please find our quotation below. Feel free to contact us if you have any questions — we look forward to working with you.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Quotation Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Valid Until</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Quotation PDF Attached</strong> — Please find the complete quotation details in the attached PDF file.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Best regards — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
        {
            "style": "Creative",
            "subject": "✨ Your Custom Quote - [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#11998e;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.25);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">✨ Your Custom Quote</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.85);">Specially prepared just for you</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.35);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Valid until [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hello <strong>[[employee]]</strong>!</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">We're excited to share this customized quotation with you! It's been specially prepared based on your requirements — take your time to review it.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:20px 24px;">
            <div style="font-size:17px;font-weight:700;color:#2e7d32;margin-bottom:10px;font-family:Georgia,serif;">📅 Quotation Validity</div>
            <div style="font-size:14px;color:#388e3c;line-height:1.65;">This quote is valid until <strong>[[date]]</strong>. Got questions? We're just a message away! 💬</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Quotation PDF Attached</strong> — Check your attachments for the complete quotation details.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;"><strong>[[company]]</strong> — Making your vision a reality ✨</p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
    ],

    # ── Order ─────────────────────────────────────────────────────────────────
    "Order": [
        {
            "style": "Professional",
            "subject": "Order Confirmation from [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Order Confirmation</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Thank you for your order</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Order #[[order_number]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Thank you for your order. Please find the order details below. We will notify you once the order is shipped.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Order Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Order No.</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[order_number]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Expected Delivery</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Order PDF Attached</strong> — Please find the complete order details in the attached PDF file.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
        {
            "style": "Modern",
            "subject": "Your Order #[[order_number]] - [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Order Confirmed ✓</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Order #[[order_number]]</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Delivery: [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hi <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">We've received your order and it's being processed. We'll update you with shipping and tracking details soon.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;text-align:center;">
          <tr><td style="padding:28px;">
            <div style="font-size:12px;color:#6b6f9a;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Order Total</div>
            <div style="font-size:38px;font-weight:700;color:#55588b;font-family:Georgia,serif;">[[amount]]</div>
            <div style="font-size:13px;color:#6b6f9a;margin-top:6px;">Expected Delivery: [[date]]</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Order PDF Attached</strong> — Check your attachments for the complete order details.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
    ],

    # ── Bill ──────────────────────────────────────────────────────────────────
    "Bill": [
        {
            "style": "Professional",
            "subject": "Bill from [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Bill</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Please find your bill details below</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Due on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Dear <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Please find your bill details below. Payment can be made through the methods outlined in the attached PDF.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;">
          <tr><td style="padding:22px 24px;">
            <div style="font-size:17px;font-weight:700;color:#55588b;margin-bottom:16px;font-family:Georgia,serif;">Bill Details</div>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid rgba(85,88,139,0.12);padding-bottom:10px;margin-bottom:10px;">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Amount</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[amount]]</td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="font-size:14px;color:#6b6f9a;font-weight:500;">Due Date</td><td style="font-size:14px;color:#55588b;font-weight:700;text-align:right;">[[date]]</td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Bill PDF Attached</strong> — Please find the complete bill details in the attached PDF file.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you for your business — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
        {
            "style": "Modern",
            "subject": "Your Bill #[[code]] - [[company]]",
            "body": """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7f8fc;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f7f8fc;padding:40px 16px;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" border="0" style="max-width:580px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <tr><td style="background-color:#55588b;padding:32px 40px 28px;">
        <table cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:rgba(255,255,255,0.2);border-radius:8px;width:36px;height:36px;text-align:center;vertical-align:middle;font-size:18px;color:#ffffff;">[[logo]]</td>
          <td style="padding-left:10px;font-size:22px;font-weight:700;color:#ffffff;font-family:Georgia,serif;">[[company]]</td>
        </tr></table>
        <div style="margin-top:20px;font-size:26px;font-weight:700;color:#ffffff;line-height:1.25;">Bill #[[code]]</div>
        <div style="margin-top:6px;font-size:14px;color:rgba(255,255,255,0.8);">Your bill is ready</div>
        <table cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;"><tr>
          <td style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:100px;padding:6px 14px;font-size:13px;color:#ffffff;">&#9679;&nbsp;Due on [[date]]</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:36px 40px;">
        <p style="margin:0 0 16px;font-size:15px;color:#1a1a2e;">Hi <strong>[[employee]]</strong>,</p>
        <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#444444;">Your bill is ready! Please review the details and process payment at your earliest convenience.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#dce2f9;border-radius:10px;margin-bottom:24px;text-align:center;">
          <tr><td style="padding:28px;">
            <div style="font-size:12px;color:#6b6f9a;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Amount Due</div>
            <div style="font-size:38px;font-weight:700;color:#55588b;font-family:Georgia,serif;">[[amount]]</div>
            <div style="font-size:13px;color:#6b6f9a;margin-top:6px;">Due by [[date]]</div>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
            <table cellpadding="0" cellspacing="0" border="0"><tr>
              <td style="font-size:18px;vertical-align:top;padding-right:10px;">📎</td>
              <td style="font-size:13px;color:#7a5f00;line-height:1.55;"><strong>Bill PDF Attached</strong> — Check your attachments for the complete bill details.</td>
            </tr></table>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f7f8fc;border-top:1px solid #e8eaf0;padding:18px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#9b9dc4;">Thank you — <strong>[[company]]</strong></p>
        <p style="margin:0;font-size:12px;color:#9b9dc4;">© 2025 Lyra ERP. All rights reserved.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>""",
            "is_hardcoded": True,
            "attach_pdf": True,
        },
    ],
}

