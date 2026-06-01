from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_code
from .forms import TaxForm, TaxGroupForm, TaxTypeForm, TaxMasterForm
from .models import Tax, TaxGroup, TaxType, TaxMaster
from company.models import Company
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from itertools import chain
from decimal import Decimal

from django.db.models import Q,Sum
from django.http import HttpResponse
import csv

def _get_current_company_country(request):
    company_code = get_company_code(request)
    company_db = getattr(request, "company_db", None)
    session_company_db = request.session.get("company_db") if hasattr(request, "session") else None
    company = None

    if company_db and company_db != "default":
        tenant_companies = Company.objects.using(company_db)
        if company_code:
            company = tenant_companies.filter(company_code=company_code).only("country").first()
        if company is None:
            company = tenant_companies.only("country").order_by("id").first()

    if company is None and company_code:
        company = Company.objects.using('default').filter(company_code=company_code).only('country').first()

    if company is None and session_company_db and session_company_db != "default":
        company = Company.objects.using('default').filter(db_name=session_company_db).only('country').first()

    if not company or not company.country:
        return ""

    return getattr(company.country, "code", "") or getattr(company.country, "name", "") or str(company.country)


def _get_current_company(request):
    company_code = get_company_code(request)
    company_db = getattr(request, "company_db", None)
    session_company_db = request.session.get("company_db") if hasattr(request, "session") else None
    company = None

    if company_db and company_db != "default":
        company = Company.objects.using(company_db).filter(company_code=company_code).first() if company_code else None
        if company is None:
            company = Company.objects.using(company_db).order_by('id').first()

    if company is None and company_code:
        company = Company.objects.using('default').filter(company_code=company_code).first()

    if company is None and session_company_db and session_company_db != "default":
        company = Company.objects.using('default').filter(db_name=session_company_db).first()

    return company


RELEVANT_COMPANY_TAX_TYPES = {
    'GST': ['GST', 'LOCAL'],
    'VAT': ['VAT', 'LOCAL'],
    'SALES': ['SALES', 'LOCAL'],
    'TURNOVER': ['TURNOVER', 'LOCAL'],
    'NONE': ['LOCAL'],
}


def add_tax_type(request):
    if request.method == 'POST':
        form = TaxTypeForm(request.POST)
        if form.is_valid():
            tax_type = form.save(commit=False)
            tax_type.country = _get_current_company_country(request)
            tax_type.save()
            messages.success(request, "Tax type added successfully.")
            return redirect_with_company('add_tax')
    else:
        form = TaxTypeForm()

    return render(request, 'Tax/tax_type_add.html', {'form': form})

def tax_type_add_modal(request):
    if request.method == 'POST':
        form = TaxTypeForm(request.POST)
        if form.is_valid():
            tax_type = form.save(commit=False)
            tax_type.country = _get_current_company_country(request)
            tax_type.save()
            return JsonResponse({
                'success': True,
                'tax_type_id': tax_type.id,
                'tax_type_name': tax_type.name,
            })

        return JsonResponse({
            'success': False,
            'html_form': render_to_string('Tax/partial_tax_type_form.html', {'form': form}, request=request)
        })

    form = TaxTypeForm()
    return render(request, 'Tax/partial_tax_type_form.html', {'form': form})

def add_tax(request):
    company = _get_current_company(request)
    company_tax_type = (company.tax_type or '').upper() if company else ''

    if request.method == 'POST':
        form = TaxForm(request.POST, show_optional_fields=False, company_tax_type=company_tax_type)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.country = _get_current_company_country(request)
            tax.save()
            messages.success(request, "Tax added successfully.")
            return redirect_with_company('tax_list')
        # ← falls through here on invalid — form re-renders with company_tax_type already set
    else:
        form = TaxForm(show_optional_fields=False, company_tax_type=company_tax_type)

    return render(request, 'Tax/tax_add.html', {
        'form': form,
        'company_tax_type': company_tax_type,   # ← also pass to template
    })


def tax_master_list(request):
    company = _get_current_company(request)
    if not company:
        messages.error(request, "Company context not found.")
        return redirect_with_company('tax_list')

    search_query = request.GET.get('q', '')
    taxes = TaxMaster.objects.filter(company=company, is_active=True)

    company_tax_type = company.tax_type or ''
    relevant_types = RELEVANT_COMPANY_TAX_TYPES.get(company_tax_type, None)
    if relevant_types is not None:
        taxes = taxes.filter(tax_type__in=relevant_types)

    if search_query:
        taxes = taxes.filter(
            Q(tax_name__icontains=search_query) |
            Q(tax_type__icontains=search_query) |
            Q(tax_scope__icontains=search_query)
        )

    taxes = taxes.order_by('tax_order', 'tax_name')

    context = {
        'taxes': taxes,
        'search_query': search_query,
        'company_tax_type': company_tax_type,
    }
    return render(request, 'Tax/tax_master_list.html', context)


def tax_master_add(request):
    company = _get_current_company(request)
    if not company:
        messages.error(request, "Company context not found.")
        return redirect_with_company('tax_list')

    if request.method == 'POST':
        form = TaxMasterForm(request.POST, company=company)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.company = company
            tax.save()
            messages.success(request, "Tax added successfully.")
            return redirect_with_company('tax_list')
    else:
        form = TaxMasterForm(company=company)

    return render(request, 'Tax/tax_add.html', {'form': form})


def tax_master_add_modal(request):
    company = _get_current_company(request)
    if request.method == 'POST':
        form = TaxMasterForm(request.POST, company=company)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.company = company
            tax.save()
            return JsonResponse({
                'success': True,
                'tax_id': tax.tax_id,
                'tax_name': tax.tax_name,
            })
        return JsonResponse({
            'success': False,
            'html_form': render_to_string('Tax/partial_tax_master_form.html', {'form': form}, request=request)
        })

    form = TaxMasterForm(company=company)
    return render(request, 'Tax/partial_tax_master_form.html', {'form': form})


def tax_master_edit(request, pk):
    company = _get_current_company(request)
    tax = get_object_or_404(TaxMaster, pk=pk, company=company)
    if request.method == 'POST':
        form = TaxMasterForm(request.POST, instance=tax, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Tax updated successfully.")
            return redirect_with_company('tax_master_list')
    else:
        form = TaxMasterForm(instance=tax, company=company)
    return render(request, 'Tax/tax_master_edit.html', {'form': form, 'tax': tax})


@require_POST
def tax_master_delete(request, pk):
    company = _get_current_company(request)
    tax = get_object_or_404(TaxMaster, pk=pk, company=company, is_active=True)
    tax.is_active = False
    tax.save(update_fields=['is_active'])
    messages.success(request, "Tax deleted successfully.")
    return redirect_with_company('tax_master_list')


def tax_list(request):
    search_query = request.GET.get('q', '')

    taxes = Tax.objects.filter(is_active=True)
    company = _get_current_company(request)
    company_tax_type = (company.tax_type or '').upper() if company else ''
    if search_query:
        taxes = taxes.filter(
            Q(taxname__icontains=search_query) |
            Q(tax_type__icontains=search_query) |
            Q(tax_scope__icontains=search_query) |
            Q(tax_method__icontains=search_query) |
            Q(applicable_on__icontains=search_query)
        )

    export = request.GET.get("export")
    if export == "tax":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="taxes.csv"'
        writer = csv.writer(response)
        writer.writerow(["Tax Name", "Tax Type", "Scope", "Rate", "Method", "Apply On", "Order", "Active"])
        for tax in taxes.order_by("tax_order", "taxname"):
            writer.writerow([
                tax.taxname or "",
                tax.tax_type or "",
                tax.tax_scope or "",
                tax.rate if tax.rate is not None else "",
                tax.tax_method or "",
                tax.applicable_on or "",
                tax.tax_order,
                "Yes" if tax.is_active else "No",
            ])
        return response

    if export == "taxgroup":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tax_groups.csv"'
        writer = csv.writer(response)
        writer.writerow(["Group Name", "Taxes"])
        tax_groups = TaxGroup.objects.prefetch_related('taxes').filter(status=True)
        if search_query:
            tax_groups = tax_groups.filter(group_name__icontains=search_query)
        for group in tax_groups.order_by("id"):
            tax_list = []
            for t in group.taxes.all():
                if t.taxtype:
                    tax_list.append(f"{t.taxname} ({t.taxtype})")
                else:
                    tax_list.append(t.taxname)
            writer.writerow([
                group.group_name or "",
                ", ".join(tax_list),
            ])
        return response

    taxes = taxes.order_by('tax_order', 'taxname')
    # Fetch tax groups if GST
    tax_groups = []
    if company_tax_type == 'GST':
        from django.db.models import Sum
        tax_groups = (
            TaxGroup.objects
            .filter(status=True)
            .prefetch_related('taxes')
            .order_by('id')
        )
        if search_query:
            tax_groups = tax_groups.filter(group_name__icontains=search_query)

        # Annotate each group with combined rate
        result = []
        for group in tax_groups:
            group.total_rate = group.taxes.filter(is_active=True).aggregate(
                total=Sum('rate')
            )['total'] or 0
            result.append(group)
        tax_groups = result
    paginator = Paginator(taxes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
   
    context = {
        "page_obj": page_obj,
        "tax_groups": tax_groups,
        "tax_count": page_obj.paginator.count,  # ✅ total taxes count
        "search_query": search_query,
        "company_code": getattr(request, "company_code", None) or request.session.get("company_code"),
        "company_tax_type": company_tax_type,
    }
    return render(request, 'Tax/tax_list.html', context)


def tax_edit(request, pk):
    tax = get_object_or_404(Tax, pk=pk)
    company = _get_current_company(request)
    company_tax_type = (company.tax_type or '').upper() if company else ''

    if request.method == 'POST':
        form = TaxForm(request.POST, request.FILES, instance=tax, show_optional_fields=False, company_tax_type=company_tax_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Tax edited successfully.")
            return redirect_with_company('tax_list')
        
    else:
        form = TaxForm(instance=tax, show_optional_fields=False, company_tax_type=company_tax_type)
    return render(request, 'Tax/tax_edit.html', {'form': form})

@require_POST
def tax_delete(request, pk):
    tax = get_object_or_404(Tax, pk=pk, is_active=True)
    # Fix: Use the correct related name for tax groups
    associated_groups = TaxGroup.objects.filter(taxes=tax)

    if associated_groups.exists():
        group_names = ", ".join([group.group_name for group in associated_groups])
        messages.error(request, f"This tax is associated with the tax group(s): {group_names} and cannot be deleted.")
        return redirect_with_company('tax_list')  # Or where you want to redirect after failure

    tax.is_active = False
    tax.save(update_fields=['is_active'])
    messages.success(request, "Tax deleted successfully.")
    return redirect_with_company('tax_list')

    if request.method == "POST":
        tax.status = False
        tax.save(update_fields=["status"])
        messages.success(request, "Tax deleted successfully.")
        return redirect_with_company('tax_list')

    # Optional: Render a confirmation template if you want a confirmation page
    return render(request, "Tax/tax_list.html", {"tax": tax})


#eg modal
def tax_add_modal(request):
    company = _get_current_company(request)
    company_tax_type = (company.tax_type or '').upper() if company else ''
    if request.method == 'POST':
        form = TaxForm(request.POST, show_optional_fields=False, company_tax_type=company_tax_type)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.country = _get_current_company_country(request)
            tax.save()
            # Return the formatted tax name like in the expense form
            formatted_name = f"{tax.taxname} - {tax.taxtype} ({tax.rate}%)"
            return JsonResponse({
                'success': True,
                'tax_id': tax.id,
                'tax_name': formatted_name
            })
        else:
            return JsonResponse({
                'success': False,
                'message': "Tax added successfully.",
                'html_form': render_to_string('Tax/partial_tax_form.html', {'form': form}, request=request)
            })
    else:
        form = TaxForm(show_optional_fields=False, company_tax_type=company_tax_type)

    return render(request, 'Tax/partial_tax_form.html', {'form': form})


def add_taxgrp(request):
    if request.method == 'POST':
        form = TaxGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tax Group added successfully.")
            return redirect_with_company('tax_list')
    else:
        form = TaxGroupForm()
    return render(request, 'Tax/add_tax_group.html', {'form': form, 'title': 'Add New Tax Group'})

def edit_taxgrp(request, pk):
    tax_group = get_object_or_404(TaxGroup, pk=pk)
    if request.method == 'POST':
        form = TaxGroupForm(request.POST, instance=tax_group)
        if form.is_valid():
            form.save()
            messages.success(request, "Tax Group edited successfully.")
            return redirect_with_company('tax_list')
    else:
        form = TaxGroupForm(instance=tax_group)
    return render(request, 'Tax/add_tax_group.html', {'form': form, 'title': 'Edit Tax Group'})

@require_POST
def taxgrp_delete(request, pk):
    tax_group = get_object_or_404(TaxGroup, pk=pk, status=True)
    tax_group.status = False
    tax_group.save(update_fields=["status"])
    messages.success(request, "Tax Group deleted successfully.")
    return redirect_with_company('tax_list')  # Redirect to your tax group list page after deletion

#to dynamically update taxes in tax group
def tax_choices_partial(request):
    form = TaxGroupForm()
    return render(request, 'Tax/tax_choices_partial.html', {'form': form})


# def get_tax(request):
#     results = []
#     company_country = _get_current_company_country(request)

#     if company_country and company_country.strip().lower() in {'india', 'in', 'ind'}:
#         taxes = TaxGroup.objects.filter(status=True).prefetch_related('taxes')
#         for h in taxes:
#             total_rate = h.taxes.filter(status=True).aggregate(total=Sum("rate"))["total"] or 0
#             results.append({
#                 "id": h.pk,
#                 "name": h.group_name,
#                 "rate": float(total_rate),
#             })
#     else:
#         taxes = Tax.objects.filter(status=True).select_related('taxtype')
#         for t in taxes:
#             results.append({
#                 "id": t.pk,
#                 "name": t.display_name,
#                 "rate": float(t.rate or 0),
#             })

#     return JsonResponse(results, safe=False)
def get_tax(request):
    print("Received request for tax data")
    results = []
    company = _get_current_company(request)
    if not company:
        return JsonResponse(results, safe=False)
    
    company_tax_type = (company.tax_type or '').upper()
    print(f"Company tax type: {company_tax_type}")
    if company_tax_type in ['TURNOVER', 'NONE']:
        results = [{"id": "none", "name": "No Tax", "rate": 0.0, "applicable_on": "Total Amount"}]
    elif company_tax_type == 'GST':
        # Load TaxGroup where taxes have GST
        groups = TaxGroup.objects.filter(status=True, taxes__tax_type='GST').distinct().prefetch_related('taxes')
        for g in groups:
            taxes_in_group = g.taxes.filter(is_active=True, tax_type='GST')
            total_rate = taxes_in_group.aggregate(total=Sum("rate"))["total"] or 0
            # Get applicable_on from first tax in group if available
            applicable_on = taxes_in_group.first().applicable_on if taxes_in_group.exists() else "Total Amount"
            if total_rate > 0:
                results.append({
                    "id": g.pk,
                    "name": g.group_name,
                    "rate": float(total_rate),
                    "applicable_on": applicable_on,
                })
        # Load IGST taxes
        igst_taxes = Tax.objects.filter(is_active=True, taxtype__name='IGST')
        for t in igst_taxes:
            results.append({
                "id": t.pk,
                "name": t.display_name,
                "rate": float(t.rate or 0),
                "applicable_on": t.applicable_on or "Total Amount",
            })
    else:
        relevant_tax_types = {
            'VAT': ['VAT'],
            'SALES': ['SALES'],
        }.get(company_tax_type, [])
        
        taxes = Tax.objects.filter(is_active=True, tax_type__in=relevant_tax_types).select_related('taxtype')
        print(f"Relevant Taxes: {[t.taxname for t in taxes]}")
        for t in taxes:
            results.append({
                "id": t.pk,
                "name": t.display_name,
                "rate": float(t.rate or 0),
                "applicable_on": t.applicable_on or "Total Amount",
            })
    
    return JsonResponse(results, safe=False)