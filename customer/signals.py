# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Customer
# from chart_of_accounts.models import ChartOfAccounts


# @receiver(post_save, sender=Customer)
# def create_customer_account(sender, instance, created, **kwargs):
#     """
#     Signal to create a chart of accounts entry under Debtors when a new customer is created
#     """
#     if created:  # Only on creation, not on updates
#         try:
#             # Get the Debtors account (should be under Accounts Receivable)
#             debtors_account = ChartOfAccounts.objects.get(name='Debtors')
            
#             # Generate code based on Debtors parent code
#             # The tree view uses code structure: parent_code + 2 digits for next level
#             existing_customer_accounts = ChartOfAccounts.objects.filter(
#                 code__startswith=debtors_account.code
#             ).exclude(id=debtors_account.id)
            
#             # Find the next number for customer account
#             existing_numbers = []
#             for acc in existing_customer_accounts:
#                 code_suffix = acc.code[len(debtors_account.code):]
#                 if code_suffix.isdigit():
#                     existing_numbers.append(int(code_suffix))
            
#             next_number = max(existing_numbers) + 1 if existing_numbers else 1
#             account_code = f"{debtors_account.code}{next_number:02d}"
            
#             # Check if account already exists
#             if not ChartOfAccounts.objects.filter(code=account_code).exists():
#                 # Determine account name based on customer type
#                 if instance.customer_type == 'company':
#                     account_name = instance.company_name or instance.customer_code
#                 else:
#                     account_name = f"{instance.first_name} {instance.last_name}".strip() or instance.customer_code
                
#                 # Create the customer account under Debtors
#                 ChartOfAccounts.objects.create(
#                     code=account_code,
#                     name=account_name,
#                     type='receivable',
#                     parent=debtors_account,
#                     is_header=False,
#                     active=instance.is_active,
#                     created_by=instance.created_by,
#                     status=instance.is_active,
#                     description=f"Customer account for {instance.customer_code}"
#                 )
#         except ChartOfAccounts.DoesNotExist:
#             # If Debtors account doesn't exist, you may want to log this or handle it
#             print(f"Warning: Debtors account not found. Customer account not created for {instance.customer_code}")
