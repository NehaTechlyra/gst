from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q

from .models import CompanyBankAccount
from .utils import ensure_bank_chart_account
from chart_of_accounts.models import ChartOfAccounts


@receiver(post_save, sender=CompanyBankAccount)
def create_bank_chart_account(sender, instance, created, **kwargs):
    """
    Ensure a ChartOfAccounts entry exists for this CompanyBankAccount.
    The chart account is created once and linked to the bank account.
    """

    ensure_bank_chart_account(instance)


@receiver(post_delete, sender=CompanyBankAccount)
def deactivate_bank_chart_account(sender, instance, **kwargs):
    """
    When a bank record is deleted, mark its related COA entry inactive.
    """
    account_name = f"{instance.bank.bank_name} - {instance.account_number}"
    ChartOfAccounts.objects.filter(
        Q(name__iexact=account_name) |
        Q(description__icontains=instance.account_number)
    ).update(status=False, active=False)
