
SMS_TEMPLATE_NAME_CHOICES = [
    ("Document Expiry Reminder", "Document Expiry Reminder"),
    ("Document Expired Reminder", "Document Expired Reminder"),
    ("Invoice", "Invoice"),
    ("Quotation", "Quotation"),
]


# Hardcoded default SMS templates
HARDCODED_SMS_TEMPLATES = {
    "Document Expiry Reminder": [
        {
            "style": "Professional",
            "content": "Dear [[employee]], your [[doc]] will expire on [[date]]. Please renew it at the earliest. - [[company]]",
            "is_hardcoded": True,
        },
        {
            "style": "Friendly",
            "content": "Hi [[employee]]! Just a reminder that your [[doc]] expires on [[date]]. Don't forget to renew it! Cheers, [[company]]",
            "is_hardcoded": True,
        },
    ],
    "Document Expired Reminder": [
        {
            "style": "Professional",
            "content": "Dear [[employee]], your [[doc]] has expired on [[date]]. Please submit the renewed document immediately. - [[company]]",
            "is_hardcoded": True,
        },
        {
            "style": "Urgent",
            "content": "URGENT: [[employee]], your [[doc]] expired on [[date]]. Please renew immediately to avoid compliance issues. - [[company]]",
            "is_hardcoded": True,
        },
    ],
    "Invoice": [
        {
            "style": "Professional",
            "content": "Dear [[employee]], your invoice for [[amount]] has been generated. Please review and process payment by [[date]]. - [[company]]",
            "is_hardcoded": True,
        },
        {
            "style": "Friendly",
            "content": "Hi [[employee]]! Your invoice of [[amount]] is ready. Payment due by [[date]]. Thank you! - [[company]]",
            "is_hardcoded": True,
        },
    ],
    "Quotation": [
        {
            "style": "Professional",
            "content": "Dear [[employee]], your quotation has been prepared. Please review it at your earliest convenience. Valid until [[date]]. - [[company]]",
            "is_hardcoded": True,
        },
        {
            "style": "Friendly",
            "content": "Hi [[employee]]! Your quote is ready. Check it out when you can - valid till [[date]]. Thanks! - [[company]]",
            "is_hardcoded": True,
        },
    ],
}