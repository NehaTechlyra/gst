"""
Cost of Goods Sold (COGS) Transfer Utility

This module handles the automatic transfer of stock cost to COGS when sales invoices are created.
It ensures that the Profit & Loss statement reflects the true profit by charging the cost of sold items.

Formula:
    Stock Reduction Dr  = Cost of items sold
    Stock In Hand       Cr = Cost of items sold

This makes the accounting accurate:
    Sales Revenue - COGS - Operating Expenses = Net Profit
"""

from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from chart_of_accounts.models import ChartOfAccounts
from journal.models import JournalEntry, JournalLine
from Items.models import Item
import logging

logger = logging.getLogger(__name__)


def get_actual_purchase_cost(item):
    """
    Get the actual cost per unit from the most recent purchase of this item.
    Uses the BillItem.price which is the actual price paid when the purchase was made.
    
    Args:
        item (Item): The Item object being sold
    
    Returns:
        Decimal: Cost per unit from the actual purchase bill
    """
    from Purchase.models import BillItem
    
    try:
        # Get the most recent BillItem (most recent purchase) for this product
        recent_bill_item = BillItem.objects.filter(
            product=item
        ).select_related('bill').order_by('-bill__date', '-id').first()
        
        if recent_bill_item and recent_bill_item.price:
            actual_cost = Decimal(str(recent_bill_item.price))
            logger.info(
                f"✓ Item '{item.name}': Using actual purchase cost ₹{actual_cost} per unit "
                f"(from Bill {recent_bill_item.bill.bill_number} dated {recent_bill_item.bill.date})"
            )
            return actual_cost
        else:
            logger.warning(f"⚠ Item '{item.name}': No purchase price found in BillItem")
    
    except Exception as e:
        logger.error(f"✗ Error getting purchase cost for item '{item.name}': {str(e)}")
    
    # Fallback to item's cost_price (last resort)
    cost_price = Decimal(str(getattr(item, 'cost_price', 0) or 0))
    if cost_price > 0:
        logger.warning(f"⚠ Item '{item.name}': Using fallback cost_price ₹{cost_price} per unit (no actual purchase found)")
    else:
        logger.error(f"✗ Item '{item.name}': No cost found anywhere - COGS will be ₹0.00")
    
    return cost_price


def calculate_item_cost_from_purchase(item, quantity_sold):
    """
    Calculate the cost of sold item based on actual purchase data.
    
    Looks for the item's actual purchase cost from BillItem records,
    falls back to item's cost_price field if no purchases found.
    
    Args:
        item (Item): The Item object being sold
        quantity_sold (Decimal): Quantity sold in this invoice
    
    Returns:
        tuple: (cost_amount, purchase_account_name)
    """
    # Get actual cost from purchase records
    cost_price = get_actual_purchase_cost(item)
    purchase_account = getattr(item, 'purchase_account', 'Stock In Hand') or 'Stock In Hand'
    
    cost_amount = cost_price * quantity_sold
    cost_amount = cost_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return cost_amount, purchase_account


def create_cogs_transfer(invoice, user=None):
    """
    Create a journal entry to transfer COGS (Cost of Goods Sold) from Stock to Expense.
    
    This entry should be created when a sales invoice is posted.
    
    Journal Entry Pattern:
        Dr: Cost of Goods Sold (Expense)   = Total cost of items sold
            Cr: Stock In Hand (Asset)      = Total cost of items sold
    
    Args:
        invoice (SalesInvoice): The sales invoice object
        user: The user creating the entry
    
    Returns:
        JournalEntry: The created journal entry, or None if failed
    """
    from sales.models import SalesInvoice, SalesInvoiceItem
    
    try:
        # Check if a non-reversal COGS entry already exists for this invoice
        existing_cogs = JournalEntry.objects.filter(
            reference=f"COGS-{invoice.inv_number}"
        ).exclude(narration__startswith='Reversal of').order_by('-id').first()

        # If there is an existing COGS entry, ensure it has not been reversed.
        # If a reversal entry exists for that journal (narration starts with 'Reversal of <entry_number>'),
        # we should allow creation of a new COGS entry (the old one was effectively reversed).
        if existing_cogs:
            try:
                reversed_exists = JournalEntry.objects.filter(
                    reference=existing_cogs.reference,
                    narration__startswith=f"Reversal of {existing_cogs.entry_number}"
                ).exists()
            except Exception:
                reversed_exists = False

            if not reversed_exists:
                logger.warning(f"COGS entry already exists for invoice {invoice.inv_number}")
                return existing_cogs
        
        # Get all items for this invoice
        invoice_items = SalesInvoiceItem.objects.filter(sales_inv=invoice)
        
        if not invoice_items.exists():
            logger.warning(f"Invoice {invoice.inv_number} has no items, skipping COGS transfer")
            return None
        
        # Calculate total COGS
        total_cogs = Decimal('0.00')
        cogs_by_account = {}  # Group COGS by source account
        
        for inv_item in invoice_items:
            quantity = Decimal(inv_item.quantity or 0)
            
            # Try to get cost from actual purchase records, not item master
            if hasattr(inv_item, 'product') and inv_item.product:
                item = inv_item.product
                
                # Get actual cost from actual purchase (BillItem.price)
                cost_per_unit = get_actual_purchase_cost(item)
                
                item_cost = cost_per_unit * quantity
                item_cost = item_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Track by purchase account
                acct_name = getattr(item, 'purchase_account', 'Stock In Hand') or 'Stock In Hand'
                if acct_name not in cogs_by_account:
                    cogs_by_account[acct_name] = Decimal('0.00')
                cogs_by_account[acct_name] += item_cost
                total_cogs += item_cost
                
                logger.info(
                    f"COGS Calculation - Invoice {invoice.inv_number}, Item '{item.name}': "
                    f"Quantity={quantity} × Cost per Unit=₹{cost_per_unit} = Total COGS=₹{item_cost}"
                )
        
        if total_cogs == Decimal('0.00'):
            logger.warning(f"No COGS calculated for invoice {invoice.inv_number}")
            return None
        
        # Generate Journal Entry Number
        last_entry = JournalEntry.objects.order_by('-id').first()
        if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JV-'):
            try:
                last_num = int(last_entry.entry_number.split('-')[1])
            except Exception:
                last_num = 0
        else:
            last_num = 0
        next_num = last_num + 1
        entry_number = f"JV-{str(next_num).zfill(5)}"
        
        # Create Journal Entry
        with transaction.atomic():
            journal = JournalEntry.objects.create(
                entry_number=entry_number,
                date=invoice.date,
                reference=f"COGS-{invoice.inv_number}",
                narration=f"COGS Transfer for Sales Invoice {invoice.inv_number}",
                created_by=user,
                updated_by=user,
                status='posted'
            )
            
            seq = 10
            total_debit = Decimal('0.00')
            total_credit = Decimal('0.00')
            
            # Debit: Cost of Goods Sold (Expense Account)
            cogs_acct = ChartOfAccounts.objects.filter(
                name__iexact='Cost of Goods Sold'
            ).first()
            
            if not cogs_acct:
                # Try alternative names
                cogs_acct = ChartOfAccounts.objects.filter(
                    name__icontains='Cost of'
                ).first()
            
            if not cogs_acct:
                logger.error("Cost of Goods Sold account not found in Chart of Accounts")
                # Try to create it if it doesn't exist
                cogs_acct = _create_cogs_account(user)
            
            if cogs_acct:
                total_cogs = total_cogs.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                JournalLine.objects.create(
                    journal=journal,
                    account=cogs_acct,
                    description=f"COGS for Invoice {invoice.inv_number}",
                    debit=total_cogs,
                    credit=Decimal('0.00'),
                    sequence=seq
                )
                total_debit += total_cogs
                seq += 10
            
            # Credit: Stock In Hand (or respective stock accounts)
            for acct_name, amount in cogs_by_account.items():
                amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if amount == Decimal('0.00'):
                    continue
                
                # Find stock account
                stock_acct = ChartOfAccounts.objects.filter(name__exact=acct_name).first()
                if not stock_acct:
                    stock_acct = ChartOfAccounts.objects.filter(name__iexact=acct_name).first()
                if not stock_acct:
                    stock_acct = ChartOfAccounts.objects.filter(name__icontains=acct_name).first()
                
                # Fallback to Stock In Hand if account not found
                if not stock_acct:
                    stock_acct = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand').first()
                    if not stock_acct:
                        stock_acct = ChartOfAccounts.objects.filter(name__icontains='Stock').first()
                
                if stock_acct:
                    JournalLine.objects.create(
                        journal=journal,
                        account=stock_acct,
                        description=f"COGS reduction for {stock_acct.name}",
                        debit=Decimal('0.00'),
                        credit=amount,
                        sequence=seq
                    )
                    total_credit += amount
                    seq += 10
                    logger.info(f"Created credit line for {stock_acct.name}: {amount}")
                else:
                    logger.error(f"Stock account '{acct_name}' not found for COGS transfer - using total_cogs for fallback")
                    # Last resort fallback - if no stock account found, use total_cogs
                    stock_acct = ChartOfAccounts.objects.filter(name__iexact='Stock In Hand').first()
                    if stock_acct:
                        JournalLine.objects.create(
                            journal=journal,
                            account=stock_acct,
                            description=f"COGS reduction (fallback)",
                            debit=Decimal('0.00'),
                            credit=total_cogs,
                            sequence=seq
                        )
                        total_credit += total_cogs
                        seq += 10
            
            # Update journal totals
            journal.total_debit = total_debit
            journal.total_credit = total_credit
            journal.save()
            
            logger.info("="*70)
            logger.info(f"✓ COGS TRANSFER JOURNAL CREATED SUCCESSFULLY")
            logger.info(f"  Journal Entry:     {entry_number}")
            logger.info(f"  Reference:         COGS-{invoice.inv_number}")
            logger.info(f"  Invoice Date:      {invoice.date}")
            logger.info(f"  Total Debit:       ₹{total_debit}")
            logger.info(f"  Total Credit:      ₹{total_credit}")
            logger.info(f"  Status:            Posted")
            logger.info("="*70)
            
            return journal
    
    except Exception as e:
        logger.exception(f"Failed to create COGS transfer for invoice {invoice.inv_number}: {str(e)}")
        return None


def _create_cogs_account(user):
    """
    Create the Cost of Goods Sold account if it doesn't exist.
    
    Args:
        user: The user creating the account
    
    Returns:
        ChartOfAccounts: The created or existing COGS account
    """
    try:
        # Find the Expenses parent account
        expense_parent = ChartOfAccounts.objects.filter(
            name__iexact='Direct Expenses'
        ).first()
        
        if not expense_parent:
            expense_parent = ChartOfAccounts.objects.filter(
                name__icontains='Expense'
            ).first()
        
        # Create COGS account
        cogs_acct = ChartOfAccounts.objects.create(
            code='COGS001',
            name='Cost of Goods Sold',
            type=expense_parent.type if expense_parent else 'Expense',
            parent=expense_parent,
            description='Cost of Goods Sold (COGS) - Transferred at time of sale',
            is_header=False,
            active=True,
            created_by=user,
            updated_by=user,
            status=True
        )
        logger.info(f"Created COGS account: {cogs_acct.name} ({cogs_acct.code})")
        return cogs_acct
    
    except Exception as e:
        logger.exception(f"Failed to create COGS account: {str(e)}")
        return None
