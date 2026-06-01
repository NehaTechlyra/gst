"""
Fallback definitions so services can import GLOBAL_ACCOUNTS/get_tax_template_for_country even
when the original definition lives in another branch or release.
"""

GLOBAL_ACCOUNTS = []


def get_tax_template_for_country(country_code):
    return []

