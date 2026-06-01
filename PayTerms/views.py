from django.shortcuts import render,redirect,get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.http import JsonResponse, HttpResponse
from .models import PayTerms
from .forms import PayTermsForm  
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
import csv

# Create your views here.
def payterm_view(request):
    search_query = request.GET.get('q', '')
    payterms = PayTerms.objects.filter(status=True)

    if search_query:
        payterms = payterms.filter(
            Q(name__icontains=search_query) 
          
        )
    payterms = payterms.order_by('id')

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="payterms.csv"'
        writer = csv.writer(response)
        writer.writerow(["Name", "Days"])
        for term in payterms:
            writer.writerow([
                term.name or "",
                term.days if term.days is not None else "",
            ])
        return response
    paginator = Paginator(payterms, 10)
    page_number = request.GET.get('page')
    payterm_page = paginator.get_page(page_number)

    return render(request, "payterm_list.html", {
        "payterms": payterm_page,
        "search_query": search_query
    })

def payterm_list(request):
    results = []
    # if query:
    payterms = PayTerms.objects.filter(status=True)
    results = [{"id": h.id, "name": h.name, "days": h.days} for h in payterms]
    return JsonResponse(results, safe=False)


@csrf_exempt
def save_payterms(request):
    if request.method == "POST":
        data = json.loads(request.body)
        last_created_id = None
        last_created_name = None
        # terms = data.get('terms', [])
        # 1. Save or update terms
        for term in data.get("terms", []):
            if term["id"]:  # update
                pt = PayTerms.objects.get(id=term["id"])
                pt.name = term["name"]
                pt.days = term["days"]
                pt.save()
            else:  # insert
                new_term = PayTerms.objects.create(name=term["name"], days=term["days"])
                last_created_id = new_term.id  # Store the ID of the newly created term
                last_created_name = new_term.name  # Store the name of the newly created term
        
        # 2. Delete terms
        for term_id in data.get("deleted", []):
            PayTerms.objects.filter(id=term_id).delete()
        
        
        return JsonResponse({"status": "success", "last_created_id": last_created_id, "last_created_name": last_created_name})
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def payterm_add(request):
    if request.method == "POST":
        form = PayTermsForm(request.POST)
        if form.is_valid():
            payterm = form.save(commit=False)
            payterm.created_by = request.user
            # payterm.updated_by = request.user
            payterm.save()
            messages.success(request, "Payment Term added successfully.")
            return redirect_with_company('payterm_view')  # Redirect to a list or detail page after saving
            
    else:
        form = PayTermsForm()

    # return render(request, "add_payterm.html", {"form": form})
    return render(request, 'add_payterm.html', {'form': form, 'title': 'Add New Payment Term'})


@login_required
def edit_payterm(request, pk):
    payterm = get_object_or_404(PayTerms, pk=pk)

    if request.method == "POST":
        form = PayTermsForm(request.POST, instance=payterm)
        if form.is_valid():
            payterm = form.save(commit=False)
            # Preserve created_by, set updated_by to current user
            if not payterm.created_by:
                payterm.created_by = request.user
            payterm.updated_by = request.user
            payterm.save()
            messages.success(request, "Payment Term edited successfully.")
            return redirect_with_company('payterm_view')  # Change redirect as per your flow
    else:
        form = PayTermsForm(instance=payterm)

    # return render(request, "add_payterm.html", {"form": form})
    return render(request, 'add_payterm.html', {'form': form, 'title': 'Edit Payment Term'})

# Delete view
@require_POST
def delete_payterm(request, pk):
    payterm = get_object_or_404(PayTerms, pk=pk)
    payterm.status = False
    payterm.save(update_fields=["status"])
    messages.success(request, "Payment Term deleted successfully.")
    return redirect_with_company('payterm_view')
        
        