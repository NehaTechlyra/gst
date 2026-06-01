# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Stock
from .forms import StockFormSet, WarehouseSelectForm 
from django.core.paginator import Paginator
from django.db.models import Q,Sum
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
import csv
from decimal import Decimal
from datetime import datetime
import logging
# Period Locking Integration
from system_settings.validators import PeriodLockEnforcer
from django.core.exceptions import PermissionDenied

# Import for Stock Detail
from Items.models import Item
from journal.models import JournalEntry, JournalLine
from django.db.models import F, Value, CharField

# Accounting imports
from journal.models import JournalEntry, JournalLine
from chart_of_accounts.models import ChartOfAccounts

logger = logging.getLogger(__name__)


def ensure_stock_adjustment_accounts_exist():
    """
    Ensure required accounts exist for manual stock entries.
    Creates: Stock In Hand (Asset) and Stock Adjustment (Expense/Income)
    Returns: (inventory_account, stock_adjustment_account)
    """
    try:
        # 1. Ensure Stock Assets parent exists
        stock_assets = ChartOfAccounts.objects.filter(
            name__iexact='Stock Assets',
            is_header=True,
            status=True
        ).first()
        
        if not stock_assets:
            stock_assets = ChartOfAccounts.objects.create(
                name='Stock Assets',
                code='1.01',
                type='1',  # Asset
                parent=None,
                is_header=True,
                status=True
            )
        
        # 2. Create/Get Stock In Hand
        inventory_account = ChartOfAccounts.objects.filter(
            name__iexact='Stock In Hand',
            status=True
        ).first()
        
        if not inventory_account:
            inventory_account = ChartOfAccounts.objects.create(
                name='Stock In Hand',
                code='1.01.01',
                type='1',  # Asset
                parent=stock_assets,
                is_header=False,
                status=True
            )
        
        # 3. Ensure Expense parent exists
        expense_parent = ChartOfAccounts.objects.filter(
            name__iexact='Expenses',
            is_header=True,
            status=True
        ).first()
        
        if not expense_parent:
            expense_parent = ChartOfAccounts.objects.create(
                name='Expenses',
                code='4',
                type='4',  # Expense
                parent=None,
                is_header=True,
                status=True
            )
        
        # 4. Create/Get Stock Adjustment
        adjustment_account = ChartOfAccounts.objects.filter(
            name__iexact='Stock Adjustment',
            status=True
        ).first()
        
        if not adjustment_account:
            adjustment_account = ChartOfAccounts.objects.create(
                name='Stock Adjustment',
                code='4.05',
                type='4',  # Expense
                parent=expense_parent,
                is_header=False,
                status=True
            )
        
        return inventory_account, adjustment_account
    except Exception as e:
        logger.error(f"Error ensuring adjustment accounts: {e}", exc_info=True)
        return None, None


def post_manual_stock_entry_journal(stock_record, user):
    """
    Post accounting entry for manually added/reduced stock.
    
    Journal Entry:
    - Positive quantity (Add): Dr Stock In Hand, Cr Stock Adjustment
    - Negative quantity (Reduce): Dr Stock Adjustment, Cr Stock In Hand
    
    This treats manual stock entry as a correction/gain to inventory.
    """
    try:
        quantity = Decimal(str(stock_record.quantity))
        if quantity == 0:
            return (True, None, "No quantity to post")
        
        # Ensure accounts exist
        inventory_account, adjustment_account = ensure_stock_adjustment_accounts_exist()
        if not inventory_account or not adjustment_account:
            logger.warning("Could not ensure adjustment accounts")
            return (False, None, "Required accounts not found")
        
        # Get item cost (use opening rate if available, otherwise average)
        cost_per_unit = Decimal('0.00')
        if hasattr(stock_record.item, 'op_rate') and stock_record.item.op_rate:
            cost_per_unit = Decimal(str(stock_record.item.op_rate))
        
        if cost_per_unit <= 0:
            logger.warning(f"No cost rate available for {stock_record.item.name}")
            return (False, None, "Item has no opening rate")
        
        # Use absolute value for calculation, but preserve sign for debit/credit logic
        abs_quantity = abs(quantity)
        entry_value = abs_quantity * cost_per_unit
        is_reduction = quantity < 0
        
        entry_reference = f"MANUAL_STOCK_{stock_record.id}"
        
        # Generate entry number
        last_jv = JournalEntry.objects.order_by('-id').first()
        if last_jv and last_jv.entry_number and last_jv.entry_number.startswith('JV-'):
            try:
                last_num = int(last_jv.entry_number.split('-')[1])
            except Exception:
                last_num = 0
        else:
            last_num = 0
        entry_number = f'JV-{str(last_num + 1).zfill(5)}'
        
        # Create journal entry
        je = JournalEntry.objects.create(
            entry_number=entry_number,
            date=datetime.now().date(),
            reference=entry_reference,
            narration=f"{'Stock Reduction' if is_reduction else 'Stock Entry'}: {stock_record.item.name} ({abs_quantity} units @ ₹{cost_per_unit}/unit)",
            total_debit=entry_value,
            total_credit=entry_value,
            status='posted',
            created_by=user,
            updated_by=user
        )
        
        if is_reduction:
            # Reduction: Dr Stock Adjustment, Cr Stock In Hand
            JournalLine.objects.create(
                journal=je,
                account=adjustment_account,
                description=f"Stock Reduction: {stock_record.item.name}",
                debit=entry_value,
                credit=Decimal('0.00'),
                sequence=10,
                status=True
            )
            
            JournalLine.objects.create(
                journal=je,
                account=inventory_account,
                description=f"Stock Reduction: {stock_record.item.name}",
                debit=Decimal('0.00'),
                credit=entry_value,
                sequence=20,
                status=True
            )
        else:
            # Addition: Dr Stock In Hand, Cr Stock Adjustment
            JournalLine.objects.create(
                journal=je,
                account=inventory_account,
                description=f"Stock Entry: {stock_record.item.name}",
                debit=entry_value,
                credit=Decimal('0.00'),
                sequence=10,
                status=True
            )
            
            JournalLine.objects.create(
                journal=je,
                account=adjustment_account,
                description=f"Stock Entry: {stock_record.item.name}",
                debit=Decimal('0.00'),
                credit=entry_value,
                sequence=20,
                status=True
            )
        
        action = "Stock reduction" if is_reduction else "Stock entry"
        logger.info(f"✓ Posted {action}: {stock_record.item.name} = ₹{entry_value}")
        return (True, je, f"✓ Posted {action} ₹{float(entry_value):.2f}")
        
    except Exception as e:
        logger.error(f"Error posting manual stock entry: {e}", exc_info=True)
        return (False, None, f"Error: {str(e)}")


def stock_list(request):
    search_query = request.GET.get('q', '')

    if request.GET.get("export") == "csv":
        export_qs = Stock.objects.filter(status=True, item__status=True)
        if search_query:
            export_qs = export_qs.filter(Q(item__name__icontains=search_query))
        export_qs = export_qs.order_by("id")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="stocks.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Quantity",
            "Expiration Date",
            "Item Name",
            "Warehouse Name",
        ])
        for stock in export_qs:
            writer.writerow([
                stock.quantity,
                stock.expiration_date or "",
                stock.item.name if stock.item_id else "",
                stock.warehouse.warehouse_name if stock.warehouse_id else "",
            ])
        return response

    stocks = (
        Stock.objects
        .filter(status=True, item__status=True)
        .values('item_id', 'item__name')
        .annotate(total_quantity=Sum('quantity'))
    )

    if search_query:
        stocks = stocks.filter(
            Q(item__name__icontains=search_query)
        )

    stocks = stocks.order_by('item__name')

    paginator = Paginator(stocks, 10)
    page_number = request.GET.get('page')
    stock_page = paginator.get_page(page_number)

    return render(request, "stock_list.html", {
        "stocks": stock_page,
        "search_query": search_query
    })



@login_required
def add_multiple_stock(request):
    # 🔒by adarshlock PERIOD LOCKING: Check if today is in a locked period
    from django.utils import timezone
    today = timezone.now().date()
    db = getattr(request, 'company_db', 'default')
    try:
        PeriodLockEnforcer.check_can_edit(today, request.user, db=db, transaction_type='stock')
    except PermissionDenied as e:
        # For AJAX requests, return JSON error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f"❌ Cannot add stock: {str(e)}"}, status=403)
        # Render form page with error modal instead of redirecting
        warehouse_form = WarehouseSelectForm()
        formset = StockFormSet(queryset=Stock.objects.none())
        return render(request, 'add_stock.html', {
            'warehouse_form': warehouse_form,
            'formset': formset,
            'error_message': str(e),
            'show_error_modal': True,
        })#by adarshlock
    
    if request.method == 'POST':
        warehouse_form = WarehouseSelectForm(request.POST)
        formset = StockFormSet(request.POST, queryset=Stock.objects.none())
        if warehouse_form.is_valid() and formset.is_valid():
            warehouse = warehouse_form.cleaned_data['warehouse']
            posted_entries = []
            failed_entries = []
            for form in formset:
                stock = form.save(commit=False)
                stock.warehouse = warehouse
                stock.created_by = request.user
                stock.updated_by = request.user
                stock.save()
                # Post accounting entry for manual stock entry
                success, je, msg = post_manual_stock_entry_journal(stock, request.user)
                if success and je:
                    posted_entries.append(f"{stock.item.name}: {msg}")
                    logger.info(f"Stock entry {stock.id} posted to journal {je.entry_number}")
                else:
                    failed_entries.append(f"{stock.item.name}: {msg or 'Failed'}")
                    logger.warning(f"Failed to post stock entry {stock.id}: {msg}")
            
            # Show success/warning messages
            if posted_entries:
                messages.success(request, f"✓ Created {len(posted_entries)} stock entries with accounting posts")
            if failed_entries:
                messages.warning(request, f"⚠ {len(failed_entries)} entries created but could not post accounting:\n" + "\n".join(failed_entries))
            return redirect_with_company('stock_list')
    else:
        warehouse_form = WarehouseSelectForm()
        formset = StockFormSet(queryset=Stock.objects.none())

    context = {'warehouse_form': warehouse_form, 'formset': formset}
    return render(request, 'add_stock.html', context)


@login_required
def edit_stock(request, pk):
    # 🔒by adarshlock PERIOD LOCKING: Check if today is in a locked period
    from django.utils import timezone
    today = timezone.now().date()
    db = getattr(request, 'company_db', 'default')
    try:
        PeriodLockEnforcer.check_can_edit(today, request.user, db=db, transaction_type='stock')
    except PermissionDenied as e:
        # For AJAX requests, return JSON error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f"❌ Cannot edit stock: {str(e)}"}, status=403)
        # Render form page with error modal instead of redirecting
        stock = get_object_or_404(Stock, pk=pk)
        form = StockForm(instance=stock)
        return render(request, 'edit_stock.html', {
            'form': form,
            'stock': stock,
            'error_message': str(e),
            'show_error_modal': True,
        })#by adarshlock
    
    stock = get_object_or_404(Stock, pk=pk)

    if request.method == "POST":
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            stock = form.save(commit=False)
            # Preserve created_by, set updated_by to current user
            if not stock.created_by:
                stock.created_by = request.user
            stock.updated_by = request.user
            stock.save()
            messages.success(request, "Stock edited successfully.")
            return redirect_with_company('stock_list')  # Change redirect as per your flow
    else:
        form = StockForm(instance=stock)

    # return render(request, "add_stock.html", {"form": form})
    return render(request, 'add_stock.html', {'form': form, 'title': 'Edit Stock'})

# Delete view
@require_POST
def delete_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    stock.status = False
    stock.save(update_fields=["status"])
    messages.success(request, "Stock deleted successfully.")
    return redirect_with_company('stock_list')
        

@login_required
def stock_detail(request, item_id):
    """
    Display comprehensive stock details for an item including:
    - Item information
    - Stock by warehouse
    - Inventory valuation
    - Stock movements/ledger
    - Related journal entries
    - Financial impact summary
    """
    item = get_object_or_404(Item, id=item_id)
    
    # Get all stock records for this item
    stocks = Stock.objects.filter(
        item=item,
        status=True
    ).select_related('warehouse').order_by('warehouse__warehouse_name')
    
    # Calculate total quantity and value across warehouses
    total_quantity = Decimal('0.00')
    total_value = Decimal('0.00')
    warehouse_summary = []
    
    cost_per_unit = Decimal(str(item.op_rate or 0))
    
    for stock in stocks:
        qty = Decimal(str(stock.quantity or 0))
        value = qty * cost_per_unit
        total_quantity += qty
        total_value += value
        
        warehouse_summary.append({
            'warehouse': stock.warehouse.warehouse_name,
            'quantity': qty,
            'value': value,
            'batch': stock.batch_number,
            'expiration': stock.expiration_date,
        })
    
    # Get related journal entries for this item's stock transactions
    # Three types: OPENING_STOCK_ITEMNAME, OPENING_STOCK_ADJUSTMENT_ITEMNAME, MANUAL_STOCK
    journal_entries = JournalEntry.objects.filter(
        Q(reference__icontains=f'OPENING_STOCK_{item.name.upper()}') |
        Q(reference__icontains=f'OPENING_STOCK_ADJUSTMENT_{item.name.upper()}') |
        (Q(reference__icontains='MANUAL_STOCK') & Q(narration__icontains=item.name))
    ).order_by('-date').select_related('created_by')[:20]  # Last 20 entries
    
    # Get journal lines for this item's stock movements
    journal_lines = []
    for je in journal_entries:
        lines = JournalLine.objects.filter(journal=je).select_related('account')
        for line in lines:
            journal_lines.append({
                'date': je.date,
                'entry_number': je.entry_number,
                'account': line.account.name,
                'description': line.description,
                'debit': line.debit,
                'credit': line.credit,
                'narration': je.narration,
                'status': je.status,
            })
    
    # Calculate financial impact - count all stock adjustments from all entry types
    total_gains = Decimal('0.00')
    total_losses = Decimal('0.00')
    
    for je in journal_entries:
        # Get all journal lines for this entry
        total_lines = JournalLine.objects.filter(journal=je)
        for line in total_lines:
            # Count any line with "Stock Adjustment" or "Stock Adjustment" account
            if 'stock adjustment' in line.account.name.lower():
                if line.debit > 0:
                    total_losses += line.debit
                if line.credit > 0:
                    total_gains += line.credit
    
    context = {
        'item': item,
        'stocks': stocks,
        'warehouse_summary': warehouse_summary,
        'total_quantity': total_quantity,
        'total_value': total_value,
        'cost_per_unit': cost_per_unit,
        'journal_entries': journal_entries,
        'journal_lines': journal_lines,
        'total_gains': total_gains,
        'total_losses': total_losses,
        'net_impact': total_gains - total_losses,
    }
    
    return render(request, 'stock/stock_detail.html', context)
