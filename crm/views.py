from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from datetime import datetime, timedelta
import json

from .models import (
    Lead, Opportunity, Update, FollowUp, LostReason, PreSalesInteraction
)
from .forms import (
    LeadForm, LeadLostForm, OpportunityForm, UpdateForm, FollowUpForm, LostReasonForm, PreSalesInteractionForm
)
from sales.models import SalesQuotation
from HR.models import Employee
from .permissions import (
    check_crm_access, can_create_leads, can_edit_leads, can_delete_leads,
    can_create_opportunities, can_edit_opportunities, can_delete_opportunities,
    can_create_updates, can_create_followups, can_edit_followups,
    can_manage_lostreasons, check_presales_access,
    can_view_leads, can_view_opportunities, can_view_presales, can_view_lostreasons, can_view_followups,
    check_dashboard_access
)


def _get_employee_for_user(user):
    """Best-effort map from logged-in Django user to HR.Employee."""
    try:
        # 1) Strongest match: email
        if getattr(user, 'email', None):
            emp = Employee.objects.filter(email__iexact=user.email).first()
            if emp:
                return emp

        # 2) App-level user mapping (legacy master user table)
        app_user = None
        try:
            from user.models import User as AppUser
            app_user = AppUser.objects.filter(usr_name=user.username).first()
            if not app_user and getattr(user, 'email', None):
                app_user = AppUser.objects.filter(usr_mail__iexact=user.email).first()
        except Exception:
            app_user = None

        candidate_names = []
        if app_user and getattr(app_user, 'usr_fname', None):
            candidate_names.append(str(app_user.usr_fname).strip())

        # 3) Django auth names
        full_name = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
        if full_name:
            candidate_names.append(full_name)
        if getattr(user, 'first_name', None):
            candidate_names.append(str(user.first_name).strip())
        if getattr(user, 'username', None):
            candidate_names.append(str(user.username).strip())

        # Deduplicate while preserving order
        seen = set()
        names = []
        for n in candidate_names:
            key = n.lower()
            if n and key not in seen:
                names.append(n)
                seen.add(key)

        for name in names:
            # Full name exact match (first + last)
            parts = [p for p in name.split() if p]
            if len(parts) >= 2:
                first = parts[0]
                last = ' '.join(parts[1:])
                emp = Employee.objects.filter(first_name__iexact=first, last_name__iexact=last).first()
                if emp:
                    return emp

            # First name exact
            emp = Employee.objects.filter(first_name__iexact=name).first()
            if emp:
                return emp

            # Fuzzy fallback
            q = Q(first_name__icontains=name) | Q(last_name__icontains=name)
            emp = Employee.objects.filter(q).first()
            if emp:
                return emp

        return None
    except Exception:
        return None


def _is_app_admin_user(user):
    """Map auth user to app user and return admin flag."""
    try:
        from user.models import User as AppUser
        app_user = AppUser.objects.filter(usr_name=user.username).first()
        if not app_user and getattr(user, 'email', None):
            app_user = AppUser.objects.filter(usr_mail__iexact=user.email).first()
        return bool(app_user and getattr(app_user, 'is_admin', False))
    except Exception:
        return False


def _has_explicit_crm_full_access(user):
    """Check explicit CRM Full Access from role permissions (no trial shortcut)."""
    try:
        from user.models import User as AppUser, RolePermission
        app_user = AppUser.objects.filter(usr_name=user.username).first()
        if not app_user and getattr(user, 'email', None):
            app_user = AppUser.objects.filter(usr_mail__iexact=user.email).first()
        if not app_user or not getattr(app_user, 'usr_roleid', None):
            return False
        role = app_user.usr_roleid
        return RolePermission.objects.filter(
            role=role,
            module__name__iexact='CRM',
            permission_type__name='Full Access',
            allowed=True,
        ).exists()
    except Exception:
        return False


def _can_view_all_crm(user):
    # Central CRM visibility override used across Leads/Opportunities/
    # Follow-ups/Pre-sales. If True, user can see all records.
    return (
        getattr(user, 'is_superuser', False)
        or _is_app_admin_user(user)
        or _has_explicit_crm_full_access(user)
    )



@login_required
def dashboard(request):
    """Main Dashboard with all statistics"""
    # Dashboard is only accessible to users with explicit 'CRM Dashboard' permission
    if not check_dashboard_access(request.user, 'View'):
        return redirect_with_company('license_restricted')
    
    has_leads_perm = can_view_leads(request.user)
    has_opportunities_perm = can_view_opportunities(request.user)
    has_presales_perm = can_view_presales(request.user)
    has_followups_perm = can_view_followups(request.user)

    now = timezone.now()
    today = now.date()
    
    # Lead Overview - only fetch if user has permission
    if has_leads_perm:
        total_leads = Lead.objects.count()
        # Exclude leads that are marked as Lost from these category counts
        hot_leads = Lead.objects.filter(priority='Hot').exclude(status='Lost').count()
        warm_leads = Lead.objects.filter(priority='Warm').exclude(status='Lost').count()
        cold_leads = Lead.objects.filter(priority='Cold').exclude(status='Lost').count()
        
        new_leads = Lead.objects.filter(status='New').exclude(status='Lost').count()
        contacted_leads = Lead.objects.filter(status='Contacted').exclude(status='Lost').count()
        interested_leads = Lead.objects.filter(status='Interested').exclude(status='Lost').count()
        not_interested_leads = Lead.objects.filter(status='Not Interested').count()
        lost_leads = Lead.objects.filter(status='Lost').count()
    else:
        total_leads = 0
        hot_leads = 0
        warm_leads = 0
        cold_leads = 0
        new_leads = 0
        contacted_leads = 0
        interested_leads = 0
        not_interested_leads = 0
        lost_leads = 0
    
    # Quotation Summary (use Sales app quotations)
    # Only count original quotations, exclude revised (quote_number ending with -R[0-9]+)
    from django.db.models import Q
    from user.utils import has_permission
    
    # Check if user has Sales Quotation permission
    has_sales_quotation_permission = has_permission(request.user, 'Sales Quotation', 'View')
    
    if has_sales_quotation_permission:
        total_quotations = SalesQuotation.objects.filter(~Q(quote_number__regex=r'-R\d+$')).count()
        quotations_sent = SalesQuotation.objects.filter(status='Sent').count()
        quotations_accepted = SalesQuotation.objects.filter(status='Accepted').count()
        quotations_rejected = SalesQuotation.objects.filter(status='Rejected').count()
    else:
        total_quotations = 0
        quotations_sent = 0
        quotations_accepted = 0
        quotations_rejected = 0
    
    # Lost Reasons Data - only if user has permission to see leads or opportunities
    lost_reasons_data = {}
    if has_leads_perm or has_opportunities_perm:
        for reason in LostReason.objects.all():
            count = Lead.objects.filter(lost_reason=reason).count()
            count += Opportunity.objects.filter(lost_reason=reason).count()
            # Quotation lost reasons now tracked in Sales app (not counted here)
            if count > 0:
                lost_reasons_data[reason.reason] = count
    
    # Follow-up Tracker - only fetch if user has permission
    if has_followups_perm:
        today_followups = FollowUp.objects.filter(
            followup_date__date=today,
            status='Pending'
        )
        overdue_followups = FollowUp.objects.filter(
            followup_date__lt=now,
            status='Pending'
        )
        upcoming_followups = FollowUp.objects.filter(
            followup_date__gt=now,
            status='Pending'
        ).order_by('followup_date')[:10]
        
        # Reminder notifications (pending follow-ups that need attention)
        reminder_followups = []
        for followup in FollowUp.objects.filter(status='Pending', assigned_to=request.user):
            reminder_time = followup.followup_date
            if followup.reminder_interval == '15min':
                reminder_time = followup.followup_date - timedelta(minutes=15)
            elif followup.reminder_interval == '1hour':
                reminder_time = followup.followup_date - timedelta(hours=1)
            elif followup.reminder_interval == '1day':
                reminder_time = followup.followup_date - timedelta(days=1)
            
            if now >= reminder_time and not followup.reminder_sent:
                reminder_followups.append(followup)
    else:
        today_followups = FollowUp.objects.none()
        overdue_followups = FollowUp.objects.none()
        upcoming_followups = FollowUp.objects.none()
        reminder_followups = []
    
    # Recent Activities
    recent_updates = Update.objects.all()[:10]
    recent_leads = Lead.objects.all()[:5]
    
    context = {
        'total_leads': total_leads,
        'hot_leads': hot_leads,
        'warm_leads': warm_leads,
        'cold_leads': cold_leads,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'interested_leads': interested_leads,
        'not_interested_leads': not_interested_leads,
        'lost_leads': lost_leads,
        'total_quotations': total_quotations,
        'quotations_sent': quotations_sent,
        'quotations_accepted': quotations_accepted,
        'quotations_rejected': quotations_rejected,
        'has_sales_quotation_permission': has_sales_quotation_permission,
        'lost_reasons_data': json.dumps(lost_reasons_data),
        'today_followups': today_followups,
        'overdue_followups': overdue_followups,
        'upcoming_followups': upcoming_followups,
        'reminder_followups': reminder_followups,
        'recent_updates': recent_updates,
        'recent_leads': recent_leads,
        'has_leads_permission': has_leads_perm,
        'has_opportunities_permission': has_opportunities_perm,
        'has_presales_permission': has_presales_perm,
        'has_followups_permission': has_followups_perm,
    }
    return render(request, 'crm/dashboard.html', context)


# ========== LEAD VIEWS ==========

@login_required
def lead_list(request):
    """List all leads"""
    # Permission: view leads
    if not can_view_leads(request.user):
        return redirect_with_company('license_restricted')

    # Determine leads visible to this user.
    # Rule: non-superusers should only see leads assigned to their mapped
    # HR.Employee. Fallback to assigned_to only when employee mapping is absent.
    leads = Lead.objects.none()
    try:
        if _can_view_all_crm(request.user):
            leads = Lead.objects.all()
        else:
            leads = Lead.objects.none()

        # Non-admin scope:
        # 1) records assigned_to current auth user (assigner workflow)
        # 2) records assigned_employee == mapped employee (employee workflow)
        if not leads.exists():
            employee_for_user = _get_employee_for_user(request.user)
            q = Q(assigned_to=request.user)
            if employee_for_user:
                q |= Q(assigned_employee=employee_for_user)
            leads = Lead.objects.filter(q).distinct()
    except Exception:
        leads = Lead.objects.none()

    # Filtering
    priority_filter = request.GET.get('priority')
    status_filter = request.GET.get('status')
    search = request.GET.get('search')
    
    if priority_filter:
        leads = leads.filter(priority=priority_filter)
    if status_filter:
        leads = leads.filter(status=status_filter)
    if search:
        leads = leads.filter(
            Q(customer_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search) |
            Q(product_interested__icontains=search)
        )
    
    context = {'leads': leads}
    return render(request, 'crm/lead_list.html', context)


@login_required
def lead_create(request):
    """Create new lead"""
    # Permission: Create lead
    if not can_create_leads(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('lead_list')
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            if not lead.assigned_to:
                lead.assigned_to = request.user
            lead.save()
            messages.success(request, 'Lead created successfully!')
            return redirect_with_company('lead_detail', pk=lead.pk)
    else:
        form = LeadForm()
    return render(request, 'crm/lead_form.html', {'form': form, 'title': 'Create Lead'})


@login_required
def lead_detail(request, pk):
    """Lead detail view with timeline"""
    lead = get_object_or_404(Lead, pk=pk)
    # Permission: view lead detail
    if not can_view_leads(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('lead_list')

    # Keep detail access aligned with list access to avoid URL-only access.
    allow_all = _can_view_all_crm(request.user)

    if not allow_all:
        permitted = False
        if lead.assigned_to_id == request.user.id:
            permitted = True
        else:
            emp = _get_employee_for_user(request.user)
            permitted = bool(emp and lead.assigned_employee and lead.assigned_employee.pk == emp.pk)

        if not permitted:
            messages.error(request, 'Permission denied')
            return redirect_with_company('lead_list')
    updates = lead.updates.all()
    followups = lead.followups.all()
    opportunities = lead.opportunities.all()
    # Show quotations linked to this lead via CRM Update created when quotation is made
    try:
        quotations = SalesQuotation.objects.filter(updates__lead=lead).distinct()
    except Exception:
        quotations = []
    # Lost reasons form and list for inline management
    lost_reasons = LostReason.objects.all()
    lost_reason_form = LostReasonForm()
    
    context = {
        'lead': lead,
        'updates': updates,
        'followups': followups,
        'opportunities': opportunities,
        'quotations': quotations,
        'lost_reasons': lost_reasons,
        'lost_reason_form': lost_reason_form,
    }
    return render(request, 'crm/lead_detail.html', context)


@login_required
def lead_edit(request, pk):
    """Edit lead"""
    lead = get_object_or_404(Lead, pk=pk)
    # Permission: Edit lead
    if not can_edit_leads(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('lead_detail', pk=lead.pk)
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lead updated successfully!')
            return redirect_with_company('lead_detail', pk=lead.pk)
    else:
        form = LeadForm(instance=lead)
    return render(request, 'crm/lead_form.html', {'form': form, 'title': 'Edit Lead', 'lead': lead})


@login_required
def lead_delete(request, pk):
    """Delete only the lead itself (no cascade to opportunities or pre-sales)."""
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        # Permission: Delete lead
        if not can_delete_leads(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('lead_list')

        lead.delete()
        messages.success(request, 'Lead deleted successfully!')
        return redirect_with_company('lead_list')
    return redirect_with_company('lead_list')


@login_required
def lead_mark_lost(request, pk):
    """Mark lead as lost with reason"""
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        # Permission: Edit lead (marking lost is an edit)
        if not can_edit_leads(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('lead_detail', pk=lead.pk)
        form = LeadLostForm(request.POST)
        if form.is_valid():
            lost_reason = form.cleaned_data['lost_reason']
            new_reason = form.cleaned_data['new_reason']
            
            if new_reason:
                # Create new lost reason
                lost_reason = LostReason.objects.create(reason=new_reason)
            
            lead.status = 'Lost'
            lead.lost_reason = lost_reason
            lead.save()
            messages.success(request, 'Lead marked as lost!')
            return redirect_with_company('lead_detail', pk=lead.pk)
    else:
        form = LeadLostForm()
    return render(request, 'crm/lead_lost.html', {'form': form, 'lead': lead})


@login_required
def lead_to_opportunity(request, pk):
    """Convert lead to opportunity"""
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        # Permission: create opportunity
        if not can_create_opportunities(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('lead_detail', pk=lead.pk)
        form = OpportunityForm(request.POST)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.lead = lead
            opportunity.priority = lead.priority
            opportunity.assigned_to = lead.assigned_to
            opportunity.assigned_employee = lead.assigned_employee
            opportunity.save()
            messages.success(request, 'Opportunity created from lead!')
            return redirect_with_company('opportunity_detail', pk=opportunity.pk)
    else:
        form = OpportunityForm(initial={'lead': lead})
    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': 'Create Opportunity from Lead', 'lead': lead})


# ========== OPPORTUNITY VIEWS ==========

@login_required
def opportunity_list(request):
    """List all opportunities"""
    # Permission: view opportunities
    if not can_view_opportunities(request.user):
        return redirect_with_company('license_restricted')
    # Same visibility pattern as leads.
    opportunities = Opportunity.objects.none()
    try:
        if _can_view_all_crm(request.user):
            opportunities = Opportunity.objects.all()
        else:
            employee_for_user = _get_employee_for_user(request.user)
            q = Q(assigned_to=request.user)
            if employee_for_user:
                q |= Q(assigned_employee=employee_for_user)
            opportunities = Opportunity.objects.filter(q).distinct()
    except Exception:
        opportunities = Opportunity.objects.none()

    status_filter = request.GET.get('status')
    if status_filter:
        opportunities = opportunities.filter(status=status_filter)

    context = {'opportunities': opportunities}
    return render(request, 'crm/opportunity_list.html', context)


@login_required
def opportunity_detail(request, pk):
    """Opportunity detail view"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    # Permission: view opportunity detail
    if not can_view_opportunities(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('opportunity_list')
    # Keep detail access aligned with list access.
    allow_all = _can_view_all_crm(request.user)

    if not allow_all:
        permitted = False
        if opportunity.assigned_to_id == request.user.id:
            permitted = True
        else:
            emp = _get_employee_for_user(request.user)
            if emp and opportunity.assigned_employee and opportunity.assigned_employee.pk == emp.pk:
                permitted = True

        if not permitted:
            messages.error(request, 'Permission denied')
            return redirect_with_company('opportunity_list')

    updates = opportunity.updates.all()
    followups = opportunity.followups.all()
    # Show quotations linked to this opportunity via CRM Update created when quotation is made
    try:
        quotations = SalesQuotation.objects.filter(updates__opportunity=opportunity).distinct()
    except Exception:
        quotations = []
    # Lost reasons form and list for inline management
    lost_reasons = LostReason.objects.all()
    lost_reason_form = LostReasonForm()
    
    context = {
        'opportunity': opportunity,
        'updates': updates,
        'followups': followups,
        'quotations': quotations,
        'lost_reasons': lost_reasons,
        'lost_reason_form': lost_reason_form,
    }
    return render(request, 'crm/opportunity_detail.html', context)


@login_required
def opportunity_edit(request, pk):
    """Edit opportunity"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    # Permission: Edit opportunity
    if not can_edit_opportunities(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('opportunity_detail', pk=opportunity.pk)
    if request.method == 'POST':
        form = OpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            form.save()
            messages.success(request, 'Opportunity updated successfully!')
            return redirect_with_company('opportunity_detail', pk=opportunity.pk)
    else:
        form = OpportunityForm(instance=opportunity)
    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': 'Edit Opportunity', 'opportunity': opportunity})


@login_required
def opportunity_delete(request, pk):
    """Delete only the opportunity itself (no cascade to parent lead or pre-sales)."""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    if request.method == 'POST':
        # Permission: Delete opportunity
        if not can_delete_opportunities(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('opportunity_list')

        opportunity.delete()
        messages.success(request, 'Opportunity deleted successfully!')
        return redirect_with_company('opportunity_list')
    return redirect_with_company('opportunity_list')


@login_required
def opportunity_mark_lost(request, pk):
    """Mark opportunity as lost"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    if request.method == 'POST':
        form = LeadLostForm(request.POST)
        if form.is_valid():
            lost_reason = form.cleaned_data['lost_reason']
            new_reason = form.cleaned_data['new_reason']
            
            if new_reason:
                lost_reason = LostReason.objects.create(reason=new_reason)
            
            opportunity.status = 'Closed Lost'
            opportunity.lost_reason = lost_reason
            opportunity.save()
            messages.success(request, 'Opportunity marked as lost!')
            return redirect_with_company('opportunity_detail', pk=opportunity.pk)
    else:
        form = LeadLostForm()
    return render(request, 'crm/opportunity_lost.html', {'form': form, 'opportunity': opportunity})





# ========== UPDATE VIEWS ==========

@login_required
def update_create(request):
    """Create communication update"""
    lead_id = request.GET.get('lead_id')
    opportunity_id = request.GET.get('opportunity_id')
    quotation_id = request.GET.get('quotation_id')
    
    # Permission: create update
    if request.method == 'POST':
        if not can_create_updates(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('dashboard')
        form = UpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.created_by = request.user
            update.save()
            messages.success(request, 'Update created successfully!')
            
            # Redirect based on related object
            if update.lead:
                return redirect_with_company('lead_detail', pk=update.lead.pk)
            elif update.opportunity:
                return redirect_with_company('opportunity_detail', pk=update.opportunity.pk)
            elif update.quotation:
                return redirect_with_company('quotation_detail', pk=update.quotation.pk)
            return redirect_with_company('dashboard')
    else:
        initial = {}
        if lead_id:
            initial['lead'] = lead_id
        if opportunity_id:
            initial['opportunity'] = opportunity_id
        if quotation_id:
            initial['quotation'] = quotation_id
        
        form = UpdateForm(initial=initial)
    
    return render(request, 'crm/update_form.html', {'form': form, 'title': 'Add Update'})


# ========== FOLLOW-UP VIEWS ==========

@login_required
def followup_list(request):
    """List all follow-ups"""
    # Permission: view follow-ups
    if not can_view_followups(request.user):
        return redirect_with_company('license_restricted')
    
    # Admin/full-access users see all.
    # Others can see:
    # 1) directly assigned follow-ups
    # 2) follow-ups linked to leads/opportunities already visible to them
    followups = FollowUp.objects.none()
    try:
        if _can_view_all_crm(request.user):
            followups = FollowUp.objects.all()
        else:
            employee_for_user = _get_employee_for_user(request.user)
            q = Q(assigned_to=request.user)
            if employee_for_user:
                q |= Q(assigned_employee=employee_for_user)
            # Include related records so assigners can track downstream actions.
            lead_scope = Q(assigned_to=request.user)
            opp_scope = Q(assigned_to=request.user)
            if employee_for_user:
                lead_scope |= Q(assigned_employee=employee_for_user)
                opp_scope |= Q(assigned_employee=employee_for_user)
            visible_lead_ids = Lead.objects.filter(lead_scope).values_list('id', flat=True)
            visible_opp_ids = Opportunity.objects.filter(opp_scope).values_list('id', flat=True)
            q |= Q(lead_id__in=visible_lead_ids) | Q(opportunity_id__in=visible_opp_ids)
            followups = FollowUp.objects.filter(q).distinct()
    except Exception:
        followups = FollowUp.objects.none()

    status_filter = request.GET.get('status')
    if status_filter:
        followups = followups.filter(status=status_filter)

    context = {'followups': followups}
    return render(request, 'crm/followup_list.html', context)


@login_required
def followup_create(request):
    """Create follow-up"""
    lead_id = request.GET.get('lead_id')
    opportunity_id = request.GET.get('opportunity_id')
    quotation_id = request.GET.get('quotation_id')
    
    # Permission: create followup
    if request.method == 'POST':
        if not can_create_followups(request.user):
            messages.error(request, 'Permission denied')
            return redirect_with_company('followup_list')
        form = FollowUpForm(request.POST)
        if form.is_valid():
            followup = form.save()
            messages.success(request, 'Follow-up created successfully!')
            
            if followup.lead:
                return redirect_with_company('lead_detail', pk=followup.lead.pk)
            elif followup.opportunity:
                return redirect_with_company('opportunity_detail', pk=followup.opportunity.pk)
            elif followup.quotation:
                return redirect_with_company('quotation_detail', pk=followup.quotation.pk)
            return redirect_with_company('followup_list')
    else:
        initial = {}
        if lead_id:
            initial['lead'] = lead_id
        if opportunity_id:
            initial['opportunity'] = opportunity_id
        if quotation_id:
            initial['quotation'] = quotation_id
        # Try to preselect the HR Employee that matches the logged-in user
        try:
            emp = Employee.objects.filter(email__iexact=request.user.email).first()
            if emp:
                initial['assigned_employee'] = emp
        except Exception:
            # fallback: leave unassigned
            pass
        
        form = FollowUpForm(initial=initial)
    
    return render(request, 'crm/followup_form.html', {'form': form, 'title': 'Create Follow-up'})


@login_required
def followup_complete(request, pk):
    """Mark follow-up as completed"""
    followup = get_object_or_404(FollowUp, pk=pk)
    # Permission: edit followup
    if not can_edit_followups(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('followup_list')

    followup.status = 'Completed'
    followup.save()
    messages.success(request, 'Follow-up marked as completed!')
    return redirect_with_company('followup_list')


# ========== QUOTATION CREATION FROM CRM ==========

@login_required
def crm_quotation_create(request):
    """
    Create a quotation from CRM Lead or Opportunity.
    Pre-fills customer data and links quotation back to opportunity.
    """
    from customer.models import Customer
    from sales.forms import SalesQuotationForm
    from sales.models import SalesQuotation
    from company.models import Company
    from currencies.models import Currency
    from django.utils.timezone import localdate
    from Items.models import Item
    from django.forms import formset_factory, modelformset_factory
    from sales.forms import SalesQuotationItemForm
    from Items.forms import ItemForm
    from sales.views import _get_current_company_country, _is_indian_company_country
    
    # Check permission
    try:
        from sales.permissions import can_create_quotations
        if not (getattr(request.user, 'is_superuser', False) or can_create_quotations(request.user)):
            messages.error(request, 'You do not have permission to create Quotations.')
            return redirect_with_company('quotation_list')
    except Exception:
        messages.error(request, 'You do not have permission to create Quotations.')
        return redirect_with_company('quotation_list')

    lead = None
    opportunity = None
    customer = None
    lead_id = request.GET.get('lead_id')
    opportunity_id = request.GET.get('opportunity_id')
    
    # Get Lead or Opportunity
    if opportunity_id:
        opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
        lead = opportunity.lead
    elif lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
    
    if not lead:
        messages.error(request, 'Lead or Opportunity not found')
        return redirect_with_company('lead_list')
    
    # Get or create Customer from Lead data
    customer_was_auto_created = False
    try:
        # Try to find existing customer by email
        if lead.email:
            customer = Customer.objects.filter(email__iexact=lead.email, is_active=True).first()
        
        # If not found, create new customer from Lead
        if not customer:
            # Parse customer name - split first and last name
            names = lead.customer_name.strip().split(' ', 1)
            first_name = names[0] if len(names) > 0 else lead.customer_name
            last_name = names[1] if len(names) > 1 else ''
            
            # Generate unique customer code
            base_code = first_name[:3].upper()
            count = Customer.objects.filter(customer_code__startswith=base_code).count()
            customer_code = f"{base_code}{count + 1:04d}"
            
            # Create customer
            customer = Customer.objects.create(
                customer_code=customer_code,
                customer_type='individual',
                first_name=first_name,
                last_name=last_name,
                email=lead.email or f"{customer_code}@crm-lead.local",
                phone=lead.phone,
                address_line_1='Pending',
                city='Pending',
                state='Pending',
                postal_code='00000',
                country='IN',  # Default to India, can be changed
                created_by=request.user,
                is_draft=True,  # ← Add this
            )
            customer_was_auto_created = True
            messages.info(request, f'New customer created: {customer.customer_code} (will be deleted if quotation is not saved)')
            
            # Track auto-created customer in session for cleanup if quotation not saved
            if 'crm_auto_customers' not in request.session:
                request.session['crm_auto_customers'] = []
            request.session['crm_auto_customers'].append(customer.pk)
            request.session.modified = True
    except Exception as e:
        messages.error(request, f'Error creating/finding customer: {str(e)}')
        if opportunity:
            return redirect_with_company('opportunity_detail', pk=opportunity.pk)
        return redirect_with_company('lead_detail', pk=lead.pk)
    
    # Get company for currency field
    try:
        cid = request.session.get('company_id')
        company = None
        if cid:
            company = Company.objects.filter(pk=cid).first()
        if not company:
            company = Company.objects.order_by('id').first()
    except Exception:
        company = None
    
    try:
        company_currencies = Currency.objects.filter(company=company, is_active=True).order_by('code') if company else Currency.objects.none()
    except Exception:
        company_currencies = Currency.objects.none()
    
    base_currency = company_currencies.filter(is_base=True).first() or company_currencies.first()
    base_currency_symbol = (base_currency.symbol or base_currency.code or '').strip() if base_currency else '₹'
    if not base_currency_symbol:
        base_currency_symbol = base_currency.code if base_currency and base_currency.code else '₹'
    base_currency_code = base_currency.code if base_currency else ''
    
    # Create quotation form with pre-filled customer
    quotation_form = SalesQuotationForm(company=company, initial={'customer': customer})
    ItemFormSet = modelformset_factory(Item, form=ItemForm, extra=0)
    item_formset = ItemFormSet(queryset=Item.objects.none())
    SalesQuotationItemFormSet = formset_factory(SalesQuotationItemForm, extra=1)
    sales_formset = SalesQuotationItemFormSet()
    
    all_items = Item.objects.all()
    company_country = _get_current_company_country(request)
    company_is_india = _is_indian_company_country(company_country)
    
    # Pass context to template
    context = {
        'quotation_form': quotation_form,
        'item_formset': item_formset,
        'sales_formset': sales_formset,
        'all_items': all_items,
        'today': localdate().isoformat(),
        'q_no': f"SQ-{SalesQuotation.objects.count() + 1:05d}",
        'lead_id': lead.pk,
        'opportunity_id': opportunity.pk if opportunity else None,
        'company_country': company_country,
        'company_is_india': company_is_india,
        'company_currencies': company_currencies,
        'company_base_currency_symbol': base_currency_symbol,
        'company_base_currency_code': base_currency_code,
        'crm_customer': customer,
        'crm_lead': lead,
        'crm_opportunity': opportunity,
        'crm_customer_auto_created': customer_was_auto_created,
        'crm_customer_id': customer.pk if customer else None,
    }
    
    return render(request, 'sales/quotation_add.html', context)


@login_required
def crm_quotation_cancel(request):
    """
    Cancel quotation creation and delete auto-created customer if not used.
    Called when user cancels from quotation form or leaves without saving.
    """
    # Clean up any auto-created customers that were never saved
    if 'crm_auto_customers' in request.session:
        try:
            from customer.models import Customer
            from sales.models import SalesQuotation
            
            auto_customers = request.session.get('crm_auto_customers', [])
            
            for customer_id in auto_customers:
                try:
                    customer = Customer.objects.get(pk=customer_id)
                    
                    # Check if this customer has any quotations
                    has_quotations = SalesQuotation.objects.filter(customer=customer).exists()
                    
                    if not has_quotations:
                        # Safe to delete - no quotations linked
                        customer_code = customer.customer_code
                        customer.delete()
                        logger.info(f"Auto-created customer {customer_code} deleted (no quotation was saved)")
                except Customer.DoesNotExist:
                    pass
                except Exception as e:
                    logger.warning(f"Error deleting auto-created customer {customer_id}: {e}")
            
            # Clear the session list
            request.session['crm_auto_customers'] = []
            request.session.modified = True
            
            if request.is_ajax() or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # If called via AJAX, return JSON
                return JsonResponse({'status': 'cleaned up'})
            
        except Exception as e:
            logger.warning(f"Error in crm_quotation_cancel cleanup: {e}")
    
    # For regular page navigation
    lead_id = request.GET.get('lead_id')
    opportunity_id = request.GET.get('opportunity_id')
    
    if opportunity_id:
        return redirect_with_company('opportunity_detail', pk=opportunity_id)
    elif lead_id:
        return redirect_with_company('lead_detail', pk=lead_id)
    else:
        return redirect_with_company('lead_list')


# ========== LOST REASON VIEWS ==========

@login_required
def lost_reason_create(request):
    """Create new lost reason. Redirect back to 'next' if provided."""
    # Permission: create lost reason
    if request.method == 'POST':
        if not can_manage_lostreasons(request.user, 'Create'):
            messages.error(request, 'Permission denied')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect_with_company(next_url)
            return redirect_with_company('dashboard')
        form = LostReasonForm(request.POST)
        next_url = request.POST.get('next') or request.GET.get('next')
        if form.is_valid():
            form.save()
            messages.success(request, 'Lost reason added successfully!')
            if next_url:
                return redirect_with_company(next_url)
            return redirect_with_company('dashboard')
    else:
        form = LostReasonForm()
        next_url = request.GET.get('next')
    
    # Get all existing lost reasons
    lost_reasons = LostReason.objects.all()
    
    return render(request, 'crm/lost_reason_form.html', {'form': form, 'title': 'Add Lost Reason', 'next': next_url, 'lost_reasons': lost_reasons})





# ========== LOST REASON MANAGEMENT VIEWS ==========

@login_required
def lost_reason_list(request):
    """List all lost reasons with counts and management actions"""
    # Permission: view lost reasons
    if not can_view_lostreasons(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('/')

    reasons = LostReason.objects.all()
    # attach counts
    data = []
    for r in reasons:
        count = Lead.objects.filter(lost_reason=r).count() + Opportunity.objects.filter(lost_reason=r).count()
        data.append({'reason': r, 'count': count})
    # include explicit permission flags for template (also available via context processor)
    context = {
        'reasons': data,
        'can_manage_crm_lostreasons': can_manage_lostreasons(request.user, 'Create'),
        'can_edit_crm_lostreasons': can_manage_lostreasons(request.user, 'Edit'),
        'can_delete_crm_lostreasons': can_manage_lostreasons(request.user, 'Delete'),
    }
    return render(request, 'crm/lost_reason_list.html', context)


@login_required
def lost_reason_edit(request, pk):
    reason = get_object_or_404(LostReason, pk=pk)
    # Permission: edit lost reason
    if request.method == 'POST':
        if not can_manage_lostreasons(request.user, 'Edit'):
            messages.error(request, 'Permission denied')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect_with_company(next_url)
            return redirect_with_company('lost_reason_list')
        form = LostReasonForm(request.POST, instance=reason)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lost reason updated successfully!')
            next_url = request.POST.get('next')
            if next_url:
                return redirect_with_company(next_url)
            return redirect_with_company('lost_reason_list')
    else:
        form = LostReasonForm(instance=reason)
        next_url = request.GET.get('next')
    return render(request, 'crm/lost_reason_form.html', {'form': form, 'title': 'Edit Lost Reason', 'next': next_url})


@login_required
def lost_reason_delete(request, pk):
    reason = get_object_or_404(LostReason, pk=pk)
    if request.method == 'POST':
        # Permission: delete lost reason
        if not can_manage_lostreasons(request.user, 'Delete'):
            messages.error(request, 'Permission denied')
            next_url = request.POST.get('next')
            if next_url:
                return redirect_with_company(next_url)
            return redirect_with_company('lost_reason_list')

        reason.delete()
        messages.success(request, 'Lost reason deleted')
        next_url = request.POST.get('next')
        if next_url:
            return redirect_with_company(next_url)
        return redirect_with_company('lost_reason_list')
    return render(request, 'crm/lost_reason_confirm_delete.html', {'reason': reason})


# ========== PRESALES VIEWS ==========

@login_required
def presales_create(request):
    # Permission: create presales interaction
    if request.method == "POST":
        if not check_presales_access(request.user, 'Create'):
            messages.error(request, 'Permission denied')
            return redirect_with_company('presales_list')

        form = PreSalesInteractionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pre-Sales interaction created successfully!')
            return redirect_with_company('presales_list')
    else:
        form = PreSalesInteractionForm()
    return render(request, 'crm/presales_form.html', {'form': form})


@login_required
def presales_list(request):
    # Permission: view presales
    if not can_view_presales(request.user):
        return redirect_with_company('license_restricted')
    # Admin/full-access users see all.
    # Others can see:
    # 1) directly employee-assigned pre-sales
    # 2) pre-sales linked to visible leads/opportunities
    presales = PreSalesInteraction.objects.none()
    try:
        if _can_view_all_crm(request.user):
            presales = PreSalesInteraction.objects.all()
        else:
            employee_for_user = _get_employee_for_user(request.user)
            q = Q()
            if employee_for_user:
                q |= Q(assigned_employee=employee_for_user)
            # Include related records so assigners can track pre-sales activity.
            lead_scope = Q(assigned_to=request.user)
            opp_scope = Q(assigned_to=request.user)
            if employee_for_user:
                lead_scope |= Q(assigned_employee=employee_for_user)
                opp_scope |= Q(assigned_employee=employee_for_user)
            visible_lead_ids = Lead.objects.filter(lead_scope).values_list('id', flat=True)
            visible_opp_ids = Opportunity.objects.filter(opp_scope).values_list('id', flat=True)
            q |= Q(lead_id__in=visible_lead_ids) | Q(opportunity_id__in=visible_opp_ids)
            presales = PreSalesInteraction.objects.filter(q).distinct()
    except Exception:
        presales = PreSalesInteraction.objects.none()

    # Filtering
    customer_name = request.GET.get('customer_name')
    interaction_type = request.GET.get('type')

    if customer_name:
        presales = presales.filter(customer_name__icontains=customer_name)
    if interaction_type:
        presales = presales.filter(type=interaction_type)

    context = {'presales': presales}
    return render(request, 'crm/presales_list.html', context)


@login_required
def presales_detail(request, pk):
    """View details of a pre-sales interaction"""
    presale = get_object_or_404(PreSalesInteraction, pk=pk)
    # Permission: view presales detail
    if not can_view_presales(request.user):
        messages.error(request, 'Permission denied')
        return redirect_with_company('presales_list')
    # Keep detail access aligned with presales_list visibility.
    if not _can_view_all_crm(request.user):
        emp = _get_employee_for_user(request.user)
        permitted = False
        if emp and presale.assigned_employee and presale.assigned_employee.pk == emp.pk:
            permitted = True
        if presale.lead_id:
            lead_scope = Q(id=presale.lead_id) & (Q(assigned_to=request.user) | Q(assigned_employee=emp))
            if Lead.objects.filter(lead_scope).exists():
                permitted = True
        if presale.opportunity_id:
            opp_scope = Q(id=presale.opportunity_id) & (Q(assigned_to=request.user) | Q(assigned_employee=emp))
            if Opportunity.objects.filter(opp_scope).exists():
                permitted = True
        if not permitted:
            messages.error(request, 'Permission denied')
            return redirect_with_company('presales_list')

    context = {'presale': presale}
    return render(request, 'crm/presales_detail.html', context)


@login_required
def presales_edit(request, pk):
    """Edit a pre-sales interaction"""
    presale = get_object_or_404(PreSalesInteraction, pk=pk)
    # Permission: edit presales
    if not check_presales_access(request.user, 'Edit'):
        messages.error(request, 'Permission denied')
        return redirect_with_company('presales_detail', pk=presale.pk)

    if request.method == 'POST':
        form = PreSalesInteractionForm(request.POST, instance=presale)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pre-Sales interaction updated successfully!')
            return redirect_with_company('presales_detail', pk=presale.pk)
    else:
        form = PreSalesInteractionForm(instance=presale)

    context = {'form': form, 'presale': presale}
    return render(request, 'crm/presales_form.html', context)


@login_required
def presales_delete(request, pk):
    """Delete a pre-sales interaction"""
    presale = get_object_or_404(PreSalesInteraction, pk=pk)
    
    if request.method == 'POST':
        # Permission: delete presales
        if not check_presales_access(request.user, 'Delete'):
            messages.error(request, 'Permission denied')
            return redirect_with_company('presales_detail', pk=presale.pk)

        presale.delete()
        messages.success(request, 'Pre-Sales interaction deleted successfully!')
        return redirect_with_company('presales_list')
    
    context = {'presale': presale}
    return render(request, 'crm/presales_confirm_delete.html', context)

