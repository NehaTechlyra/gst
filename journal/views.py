from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.utils import IntegrityError
from django.urls import reverse
from django.http import JsonResponse
from .models import JournalEntry, JournalLine
from .permissions import can_view_journal, can_create_journal, can_edit_journal, can_delete_journal
from .forms import JournalEntryForm, JournalLineForm, JournalLineFormSet
from chart_of_accounts.permissions import (
    can_view_balance_sheet, can_view_profit_loss, can_view_trial_balance, can_view_cash_flow
)
import logging

logger = logging.getLogger(__name__)

@login_required
def journal_list(request):
    # View for displaying list of all journal entries
    # Orders by newest date first, then by entry number
    # Permission: require journal view access
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_view_journal(request.user)):
            messages.error(request, 'You do not have permission to view journal entries.')
            return redirect_with_company('home')
    except Exception:
        messages.error(request, 'You do not have permission to view journal entries.')
        return redirect_with_company('home')

    journal_list = JournalEntry.objects.all().order_by('-date', '-entry_number')
    paginator = Paginator(journal_list, 10)  # Show 10 entries per page
    page = request.GET.get('page')
    journals = paginator.get_page(page)
    context = {
        'journals': journals,
        'can_create': (getattr(request.user, 'is_superuser', False) or can_create_journal(request.user)),
        'can_edit': (getattr(request.user, 'is_superuser', False) or can_edit_journal(request.user)),
        'can_delete': (getattr(request.user, 'is_superuser', False) or can_delete_journal(request.user)),
    }
    return render(request, 'journal/journal_list.html', context)

@login_required
def journal_detail(request, pk):
    # View for showing details of a specific journal entry
    # Shows header info and all related debit/credit lines
    journal = get_object_or_404(JournalEntry, pk=pk)
    try:
        has_reports_access = (
            can_view_balance_sheet(request.user)
            or can_view_profit_loss(request.user)
            or can_view_trial_balance(request.user)
            or can_view_cash_flow(request.user)
        )
        if not (getattr(request.user, 'is_superuser', False) or can_view_journal(request.user) or has_reports_access):
            messages.error(request, 'You do not have permission to view this journal entry.')
            return redirect_with_company('journal_list')
    except Exception:
        messages.error(request, 'You do not have permission to view this journal entry.')
        return redirect_with_company('journal_list')

    return render(request, 'journal/journal_detail.html', {'journal': journal})

@login_required
@transaction.atomic  # Ensures all database changes happen together or not at all
def journal_create(request):
    # Create a formset for handling multiple journal lines
    # - JournalEntry is the parent model
    # - JournalLine is the child model (individual debit/credit lines)
    # - extra=1 means show 1 extra empty line form beyond the minimum
    # - min_num=2 requires at least 2 lines (for debit and credit)
    LineFormSet = inlineformset_factory(
        JournalEntry, JournalLine,
        form=JournalLineForm,
        formset=JournalLineFormSet,
        extra=0,
        can_delete=True,
        min_num=2,
    )

    try:
        if not (getattr(request.user, 'is_superuser', False) or can_create_journal(request.user)):
            messages.error(request, 'You do not have permission to create journal entries.')
            return redirect_with_company('journal_list')
    except Exception:
        messages.error(request, 'You do not have permission to create journal entries.')
        return redirect_with_company('journal_list')

    if request.method == 'POST':
        # ✅ CHECK PERIOD LOCK BEFORE CREATING JOURNAL ENTRY
        from datetime import datetime
        from django.core.exceptions import PermissionDenied
        from system_settings.validators import PeriodLockEnforcer
        
        db = getattr(request, 'company_db', 'default')
        date_str = request.POST.get('date')
        if date_str:
            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if isinstance(date_str, str) else date_str
            except:
                entry_date = None
            
            if entry_date:
                try:
                    PeriodLockEnforcer.check_can_edit(entry_date, request.user, db=db, transaction_type='journal')
                except PermissionDenied as e:
                    # Render form page with error modal instead of redirecting
                    form = JournalEntryForm()
                    formset = LineFormSet(instance=JournalEntry())
                    return render(request, 'journal/journal_form.html', {
                        'form': form,
                        'formset': formset,
                        'title': 'Create Journal Entry',
                        'error_message': str(e),
                        'show_error_modal': True,
                    })
        
        # Handle form submission
        form = JournalEntryForm(request.POST)
        # To ensure we always have a `formset` object for rendering (even when `form` is invalid),
        # create a temporary unsaved instance to bind the formset to. If the form later validates,
        # we'll rebind the formset to the real journal instance before saving.
        temp_journal = JournalEntry()
        formset = LineFormSet(request.POST, instance=temp_journal)

        if form.is_valid():
            # Save journal entry but don't commit yet
            journal = form.save(commit=False)

            # Set audit fields
            journal.created_by = request.user
            journal.updated_by = request.user

            # Set status to posted
            journal.status = 'posted'
            formset = LineFormSet(request.POST, instance=journal)
            if formset.is_valid():
                # Generate sequential entry number with retry logic for race conditions
                max_retries = 5
                retry_count = 0
                saved = False
                
                while not saved and retry_count < max_retries:
                    try:
                        # Find highest numeric entry number
                        all_entries = JournalEntry.objects.filter(entry_number__startswith='JV-')
                        highest_num = 0
                        
                        for entry in all_entries:
                            try:
                                num = int(entry.entry_number.split('-')[1])
                                if num > highest_num:
                                    highest_num = num
                            except (IndexError, ValueError):
                                # Skip entries with invalid format
                                pass
                        
                        # Generate next number
                        journal.entry_number = f'JV-{str(highest_num + 1).zfill(5)}'
                        
                        # Save both header and lines if everything is valid
                        journal.save()
                        formset.save()
                        
                        # Recalculate totals after saving lines
                        journal.total_debit = sum(line.debit or 0 for line in journal.lines.all())
                        journal.total_credit = sum(line.credit or 0 for line in journal.lines.all())
                        journal.save()
                        
                        saved = True
                        logger.info(f"✓ Journal entry created: {journal.entry_number}")
                        messages.success(request, 'Journal entry created successfully.')
                        return redirect_with_company('journal_detail', pk=journal.pk)
                        
                    except IntegrityError as e:
                        # Handle race condition: another entry was created with same number
                        retry_count += 1
                        logger.warning(f"⚠ Duplicate entry number collision, retrying ({retry_count}/{max_retries})...")
                        transaction.rollback()  # Rollback failed transaction
                        
                        if retry_count >= max_retries:
                            messages.error(request, 'Unable to generate unique entry number after multiple attempts. Please try again.')
                            logger.error(f"✗ Failed to create journal entry after {max_retries} retries: {e}")
                            break
    else:
        # Display empty form for new entry
        form = JournalEntryForm()
        # Bind formset to a new unsaved JournalEntry instance so management_form is present
        formset = LineFormSet(instance=JournalEntry())

    # Render the form template with both header form and line formset
    return render(request, 'journal/journal_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Journal Entry'
    })


@login_required
@transaction.atomic
def journal_edit(request, pk):
    # Get the existing journal entry or show 404 if not found
    journal = get_object_or_404(JournalEntry, pk=pk)
    
    # Journal can be edited regardless of status

    # Create formset for editing lines
    # Only show 1 extra line form since this is an edit
    LineFormSet = inlineformset_factory(
        JournalEntry, JournalLine,
        form=JournalLineForm,
        formset=JournalLineFormSet,
        extra=1,  # One extra empty form
        can_delete=True,  # Allow deleting lines
        min_num=2,  # Still require minimum 2 lines
    )

    if request.method == 'POST':
        # \u2705 CHECK PERIOD LOCK BEFORE EDITING JOURNAL ENTRY
        from datetime import datetime
        from django.core.exceptions import PermissionDenied
        from system_settings.validators import PeriodLockEnforcer
        
        db = getattr(request, 'company_db', 'default')
        try:
            PeriodLockEnforcer.check_can_edit(journal.date, request.user, db=db, transaction_type='journal')
        except PermissionDenied as e:
            # For AJAX requests, return JSON error response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': f"❌ Cannot edit journal entry: {str(e)}"}, status=403)
            # Render form page with error modal instead of redirecting
            form = JournalEntryForm(instance=journal)
            LineFormSet = inlineformset_factory(
                JournalEntry, JournalLine,
                form=JournalLineForm,
                formset=JournalLineFormSet,
                extra=1,
                can_delete=True,
                min_num=2,
            )
            formset = LineFormSet(instance=journal)
            return render(request, 'journal/journal_form.html', {
                'form': form,
                'formset': formset,
                'title': 'Edit Journal Entry',
                'error_message': str(e),
                'show_error_modal': True,
            })
        
        # Handle form submission
        form = JournalEntryForm(request.POST, instance=journal)
        try:
            if not (getattr(request.user, 'is_superuser', False) or can_edit_journal(request.user)):
                messages.error(request, 'You do not have permission to edit journal entries.')
                return redirect_with_company('journal_detail', pk=journal.pk)
        except Exception:
            messages.error(request, 'You do not have permission to edit journal entries.')
            return redirect_with_company('journal_detail', pk=journal.pk)

        if form.is_valid():
            # Update the journal entry
            journal = form.save(commit=False)
            journal.updated_by = request.user  # Track who modified it
            
            # Handle the journal lines
            formset = LineFormSet(request.POST, instance=journal)
            if formset.is_valid():
                journal.save()
                formset.save()
                # Recalculate totals after saving lines
                journal.total_debit = sum(line.debit or 0 for line in journal.lines.all())
                journal.total_credit = sum(line.credit or 0 for line in journal.lines.all())
                journal.save()
                messages.success(request, 'Journal entry updated successfully.')
                return redirect_with_company('journal_detail', pk=journal.pk)
    else:
        # Display form with existing data
        form = JournalEntryForm(instance=journal)
        formset = LineFormSet(instance=journal)

    # Render form template with existing data
    return render(request, 'journal/journal_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Edit Journal Entry'
    })



@login_required
def journal_delete(request, pk):
    """Delete a journal entry"""
    # Permission check first
    try:
        if not (getattr(request.user, 'is_superuser', False) or can_delete_journal(request.user)):
            error_msg = 'You do not have permission to delete journal entries.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            messages.error(request, error_msg)
            return redirect_with_company('journal_list')
    except Exception:
        error_msg = 'You do not have permission to delete journal entries.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=403)
        messages.error(request, error_msg)
        return redirect_with_company('journal_list')

    # Now get the journal entry
    db = getattr(request, 'company_db', 'default')
    try:
        journal = JournalEntry.objects.using(db).get(pk=pk)
    except JournalEntry.DoesNotExist:
        error_msg = 'Journal entry not found.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=404)
        messages.error(request, error_msg)
        return redirect_with_company('journal_list')
    
    # ✅ CHECK PERIOD LOCK BEFORE DELETING JOURNAL ENTRY
    from django.core.exceptions import PermissionDenied
    from system_settings.validators import PeriodLockEnforcer
    
    try:
        PeriodLockEnforcer.check_can_edit(journal.date, request.user, db=db, transaction_type='journal')
    except PermissionDenied as e:
        # For AJAX requests, return JSON error response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=403)
        # Redirect to list with error message (for non-AJAX delete)
        messages.error(request, str(e))
        return redirect_with_company('journal_list')

    # Delete the journal entry and its lines (cascading delete will handle lines)  
    journal.delete(using=db)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Journal entry deleted successfully.'})
    
    messages.success(request, 'Journal entry deleted successfully.')
    return redirect_with_company('journal_list')
