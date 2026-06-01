# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from Lyraerp.utils.redirect_utils import redirect_with_company
from django.contrib.auth.decorators import login_required
from .models import Customer, GstTreatment
from company.models import Company
from .forms import CustomerForm  
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
import random
from currencies.models import Currency
from django import forms as django_forms

def customer_list(request):
    search_query = request.GET.get('q', '')
    customers = Customer.objects.all().filter(is_active=True, is_draft=False)  # Only show active customers

    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    customers = customers.order_by('-id')
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    customer_page = paginator.get_page(page_number)

    # permission helpers
    try:
        from sales.permissions import (
            can_view_customers, can_create_customers,
            can_edit_customers, can_delete_customers,
        )
    except Exception:
        # Fallback safe defaults: only superusers allowed
        def can_view_customers(u):
            return getattr(u, 'is_superuser', False)
        def can_edit_customers(u):
            return getattr(u, 'is_superuser', False)
        def can_delete_customers(u):
            return getattr(u, 'is_superuser', False)

    # Enforce view permission
    if not can_view_customers(request.user):
        messages.error(request, "You do not have permission to view customers.")
        return redirect_with_company('/')

    return render(request, "customer/customer_list.html", {
        "customers": customer_page,
        "search_query": search_query,
        'can_create_customers': can_create_customers(request.user),
        'can_edit_customers': can_edit_customers(request.user),
        'can_delete_customers': can_delete_customers(request.user),
    })


@login_required
def add_customer(request):
    # Permission helpers
    try:
        from sales.permissions import can_create_customers, can_edit_customers
    except Exception:
        def can_create_customers(u):
            return getattr(u, 'is_superuser', False)
        def can_edit_customers(u):
            return getattr(u, 'is_superuser', False)

    if request.method == "POST":
        # Check if this is an AJAX request for the modal
        # determine company for currency choices
        try:
            cid = request.session.get('company_id')
            company = None
            if cid:
                company = Company.objects.filter(pk=cid).first()
            if not company:
                company = Company.objects.order_by('id').first()
        except Exception:
            company = None

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = CustomerForm(request.POST, company=company)
            if form.is_valid():
                customer = form.save(commit=False)
                customer.created_by = request.user
                # ✅ Store request context for activity logging to find correct company_db
                customer._current_request = request
                customer.updated_by = request.user
                customer.save()
                # Build name safely and treat literal 'None' as empty
                def _clean_part(v):
                    if not v:
                        return ''
                    try:
                        s = str(v).strip()
                    except Exception:
                        return ''
                    return '' if s.lower() == 'none' else s

                first = _clean_part(customer.first_name)
                last = _clean_part(customer.last_name)
                display_name = ' '.join([p for p in (first, last) if p]).strip()
                return JsonResponse({
                    'success': True,
                    'id': customer.id,
                    'name': display_name
                })
            else:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        
        # Block POST if no create permission
        if not can_create_customers(request.user):
            messages.error(request, "You do not have permission to create customers.")
            return redirect_with_company('customer_list')

        form = CustomerForm(request.POST, company=company)
        if form.is_valid():
            customer = form.save(commit=False)
            # Ensure customer's preferred currency defaults to the organisation base currency
            try:
                cid = request.session.get('company_id')
                company = None
                if cid:
                    company = Company.objects.filter(pk=cid).first()
                if not company:
                    company = Company.objects.order_by('id').first()
                if company and (not customer.currency or customer.currency.strip() == ''):
                    customer.currency = (company.base_currency or '').strip().upper()[:10]
            except Exception:
                pass
            customer.created_by = request.user
            customer.updated_by = request.user
            customer.save()
            
            # Save contact persons if provided
            contact_names = request.POST.getlist('contact_name')
            contact_emails = request.POST.getlist('contact_email')
            contact_phones = request.POST.getlist('contact_phone')
            # Clear existing contacts for new customer (none) - just create
            from .models import ContactPerson
            for name, email, phone in zip(contact_names, contact_emails, contact_phones):
                if name.strip() or email.strip() or phone.strip():
                    ContactPerson.objects.create(
                        customer=customer,
                        name=name.strip(),
                        email=email.strip(),
                        phone=phone.strip()
                    )

            # Create vendor if is_also_vendor is checked — after customer contacts are saved
            if customer.is_vendor:
                from Purchase.models import Vendor, ContactPerson as VendorContact
                try:
                    vendor = Vendor.objects.create(
                        vendor_code=customer.customer_code,
                        vendor_type=customer.customer_type,
                        first_name=customer.first_name,
                        last_name=customer.last_name,
                        company_name=customer.company_name,
                        email=customer.email,
                        phone=customer.phone,
                        mobile=customer.mobile,
                        tax_number=customer.gst_number,
                        address_line_1=customer.address_line_1,
                        address_line_2=customer.address_line_2,
                        city=customer.city,
                        postal_code=customer.postal_code,
                        state=customer.state,
                        country=customer.country,
                        shipping_address_line_1=customer.shipping_address_line_1,
                        shipping_address_line_2=customer.shipping_address_line_2,
                        shipping_city=customer.shipping_city,
                        shipping_postal_code=customer.shipping_postal_code,
                        shipping_state=customer.shipping_state,
                        shipping_country=customer.shipping_country,
                        pan_number=customer.pan_number,
                        tax_preference= customer.tax_preference,
                        exemption_reason=customer.exemption_reason,
                        currency= customer.currency,
                        payment_terms= customer.payment_terms,
                        opening_balance=customer.opening_balance,
                        gst_treatment=customer.gst_treatment,
                        is_customer=customer.is_vendor,
                        created_at=customer.created_at,
                        updated_at=customer.updated_at,
                        created_by=customer.created_by,
                        updated_by=customer.updated_by,
                        is_active=customer.is_active,
                    )
                    # Copy contact persons from customer to vendor
                    cust_contacts = ContactPerson.objects.filter(customer=customer)
                    for cc in cust_contacts:
                        VendorContact.objects.create(
                            vendor=vendor,
                            name=cc.name,
                            email=cc.email,
                            phone=cc.phone
                        )
                    messages.success(request, "Customer and Vendor created successfully.")
                except Exception as e:
                    # Log the error but don't fail the customer creation
                    print(f"Warning: Could not create vendor for customer {customer.id}: {str(e)}")
                    messages.warning(request, f"Customer created, but vendor creation failed: {str(e)}")
            
            messages.success(request, "Customer added successfully.")
            return redirect_with_company('customer_list')  # Redirect to a list or detail page after saving
            
            
    else:
        # prepare company for GET form rendering
        try:
            cid = request.session.get('company_id')
            company = None
            if cid:
                company = Company.objects.filter(pk=cid).first()
            if not company:
                company = Company.objects.order_by('id').first()
        except Exception:
            company = None

        form = CustomerForm(company=company)
        
        # Check if this is an AJAX request for the modal
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Return just the form content for AJAX requests
            return render(request, 'customer/add_customer.html', {
                'form': form,
                'title': 'Add New Customer',
            })

    # For GET show/hide Save button based on permission
    return render(request, 'customer/add_customer.html', {
        'form': form,
        'title': 'Add New Customer',
        'can_create_customers': can_create_customers(request.user),
        'can_edit_customers': can_edit_customers(request.user),
    })



@login_required
def edit_customer(request, pk):
    # Permission helper
    try:
        from sales.permissions import can_edit_customers
    except Exception:
        def can_edit_customers(u):
            return getattr(u, 'is_superuser', False)

    customer = get_object_or_404(Customer, pk=pk)
    # determine company for currency choices
    try:
        cid = request.session.get('company_id')
        company = None
        if cid:
            company = Company.objects.filter(pk=cid).first()
        if not company:
            company = Company.objects.order_by('id').first()
    except Exception:
        company = None
    
    if request.method == "POST":
        print("=== SHIPPING DEBUG ===")
        print("shipping_address_line_1:", request.POST.get('shipping_address_line_1'))
        print("shipping_city:", request.POST.get('shipping_city'))
        print("shipping_country:", request.POST.get('shipping_country'))
        print("All POST keys:", list(request.POST.keys()))
        # Block POST if no edit permission
        if not can_edit_customers(request.user):
            messages.error(request, "You do not have permission to edit customers.")
            return redirect_with_company('customer_list')

        form = CustomerForm(request.POST, instance=customer, company=company)
        if form.is_valid():
            customer = form.save(commit=False)
            # Ensure customer's preferred currency defaults to the organisation base currency
            try:
                cid = request.session.get('company_id')
                company = None
                if cid:
                    company = Company.objects.filter(pk=cid).first()
                if not company:
                    company = Company.objects.order_by('id').first()
                if company and (not customer.currency or customer.currency.strip() == ''):
                    customer.currency = (company.base_currency or '').strip().upper()[:10]
            except Exception:
                pass
            customer.updated_by = request.user
            customer._current_request = request

            customer.save()
            
            # Update contact persons
            from .models import ContactPerson
            # Delete existing contacts
            ContactPerson.objects.filter(customer=customer).delete()
            
            # Add new/updated contacts
            contact_names = request.POST.getlist('contact_name')
            contact_emails = request.POST.getlist('contact_email')
            contact_phones = request.POST.getlist('contact_phone')
            
            for name, email, phone in zip(contact_names, contact_emails, contact_phones):
                if (name and name.strip()) or (email and email.strip()) or (phone and phone.strip()):
                    ContactPerson.objects.create(
                        customer=customer,
                        name=(name or '').strip(),
                        email=(email or '').strip(),
                        phone=(phone or '').strip()
                    )
            from Purchase.models import Vendor, ContactPerson as VendorContact
            if customer.is_vendor:
            # Sync with vendor if is_vendor is checked
                vendor = Vendor.objects.filter(email=customer.email).first()
                if not vendor:
                    try:
                        vendor = Vendor.objects.create(
                            vendor_code=customer.customer_code,
                            vendor_type=customer.customer_type,
                            first_name=customer.first_name,
                            last_name=customer.last_name,
                            company_name=customer.company_name,
                            email=customer.email,
                            phone=customer.phone,
                            mobile=customer.mobile,
                            tax_number=customer.gst_number,
                            address_line_1=customer.address_line_1,
                            address_line_2=customer.address_line_2,
                            city=customer.city,
                            postal_code=customer.postal_code,
                            state=customer.state,
                            country=customer.country,
                            shipping_address_line_1=customer.shipping_address_line_1,
                            shipping_address_line_2=customer.shipping_address_line_2,
                            shipping_city=customer.shipping_city,
                            shipping_postal_code=customer.shipping_postal_code,
                            shipping_state=customer.shipping_state,
                            shipping_country=customer.shipping_country,
                            pan_number=customer.pan_number,
                            tax_preference= customer.tax_preference,
                            exemption_reason=customer.exemption_reason,
                            currency= customer.currency,
                            payment_terms= customer.payment_terms,
                            opening_balance=customer.opening_balance,
                            gst_treatment=customer.gst_treatment,
                            is_customer=customer.is_vendor,
                            created_at=customer.created_at,
                            updated_at=customer.updated_at,
                            created_by=customer.created_by,
                            updated_by=customer.updated_by,
                            is_active=customer.is_active,
                            
                        )
                    except Exception as e:
                        print(f"Warning: Could not create vendor for customer {customer.id}: {str(e)}")
                        messages.warning(request, f"Customer updated, but vendor creation failed: {str(e)}")
                        return redirect_with_company('customer_list')

                # Replace vendor contact persons to mirror customer contacts
                try:
                    VendorContact.objects.filter(vendor=vendor).delete()
                    cust_contacts = ContactPerson.objects.filter(customer=customer)
                    for cc in cust_contacts:
                        VendorContact.objects.create(
                            vendor=vendor,
                            name=cc.name,
                            email=cc.email,
                            phone=cc.phone
                        )
                except Exception as e:
                    print(f"Warning: Could not sync vendor contacts for customer {customer.id}: {str(e)}")
                    messages.warning(request, f"Customer updated, but syncing vendor contacts failed: {str(e)}")
            
            messages.success(request, "Customer updated successfully.")
            return redirect_with_company('customer_list')
    else:
        form = CustomerForm(instance=customer, company=company)
        # If customer's currency is stored as a code (CharField), map it back
        # to a Currency instance so the ModelChoiceField shows correctly.
        try:
            code = (getattr(customer, 'currency', '') or '').strip().upper()[:3]
            if code:
                cur = Currency.objects.filter(company=company, code=code, is_active=True).first()
                if cur:
                    # Use currency code (e.g., 'AED') for the form initial so
                    # readonly/display fields show the code instead of the numeric PK.
                    form.initial['currency'] = (cur.code or '').strip().upper()
        except Exception:
            pass
    
    # Get existing contact persons
    contacts = customer.contact_persons.all()
    
    return render(request, 'customer/add_customer.html', {
        'form': form,
        'title': 'Edit Customer',
        'contacts': contacts,
        'can_edit_customers': can_edit_customers(request.user),
    })
# Delete view
@require_POST
@login_required
def delete_customer(request, pk):
    try:
        from sales.permissions import can_delete_customers
    except Exception:
        def can_delete_customers(u):
            return getattr(u, 'is_superuser', False)

    if not can_delete_customers(request.user):
        messages.error(request, "You do not have permission to delete customers.")
        return redirect_with_company('customer_list')

    customer = get_object_or_404(Customer, pk=pk)
    try:
        customer.is_active = False
        customer.save(update_fields=["is_active"])
        messages.success(request, "Customer deactivated successfully.")
    except ProtectedError:
        messages.error(
            request,
            "Cannot delete this customer because it is used in other records."
        )
    except IntegrityError:
        messages.error(
            request,
            "Cannot delete this customer because it is linked to other data."
        )
    except Exception as e:
        messages.error(request, f"Unable to delete customer: {str(e)}")
    return redirect_with_company('customer_list')

@login_required
def generate_customer_code(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'code': '', 'message': 'Name is required'})
        
        # Generate code: first 3 letters uppercased + 3 random digits
        prefix = ''.join([c.upper() for c in name[:3] if c.isalpha()])  # e.g., "ABC"
        if len(prefix) < 3:
            prefix = prefix.ljust(3, 'X')[:3]
        
        # Check existing codes with this prefix and find next number
        base_codes = Customer.objects.filter(
            customer_code__startswith=prefix
        ).values_list('customer_code', flat=True)
        
        numbers = []
        for code in base_codes:
            if len(code) >= 6 and code[:3] == prefix:
                try:
                    numbers.append(int(code[3:]))
                except ValueError:
                    pass
        
        next_num = 1
        if numbers:
            next_num = max(numbers) + 1
        
        code = f"{prefix}{next_num:03d}"  # e.g., "ABC001", "ABC999"
        
        # Ensure uniqueness (fallback random suffix if collision)
        while Customer.objects.filter(customer_code=code).exists():
            suffix = str(random.randint(100, 999))
            code = f"{prefix}{suffix}"
            next_num += 1
            if next_num > 999:
                break
        
        return JsonResponse({'success': True, 'code': code})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})
