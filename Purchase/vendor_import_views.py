"""
Vendor Import Wizard – vendor_import_views.py
Mapped exactly to your Vendor model fields.
Place in Purchase/vendor_import_views.py  (or wherever your vendor app lives)
"""

import csv
import io
import re
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ─────────────────────────────────────────────────────────────────────────────
# Field definitions
# Format: (csv_key, display_label, required, section, notes)
# ─────────────────────────────────────────────────────────────────────────────
IMPORT_FIELDS = [
    # Basic Info
    ("vendor_type",    "Vendor Type (individual/company)",   False, "basic",    "individual or company"),
    ("first_name",       "First Name",                           False, "basic",    ""),
    ("last_name",        "Last Name",                            False, "basic",    ""),
    ("company_name",     "Company Name",                         False, "basic",    "Required if type=company"),
    ("email",            "Email",                                True,  "basic",    "Must be unique"),
    ("phone",            "Phone",                                False, "basic",    ""),
    ("mobile",           "Mobile",                               False, "basic",    ""),
    ("is_customer",      "Is Customer (true/false)",             False, "basic",    ""),

    # GST / Tax
    ("gst_number",       "GST Number",                           False, "tax",      ""),
    ("pan_number",       "PAN Number",                           False, "tax",      ""),
    ("tax_preference",   "Tax Preference (taxable/tax_exempt)",  False, "tax",      ""),
    ("exemption_reason", "Exemption Reason",                     False, "tax",      ""),
    ("gst_treatment",    "GST Treatment",                        False, "tax",      "Name of GstTreatment"),

    # Financial
    ("currency",         "Currency",                             False, "financial","e.g. INR, USD"),
    ("payment_terms",    "Payment Terms",                        False, "financial","Name of PayTerms"),
    ("opening_balance",  "Opening Balance",                      False, "financial",""),

    # Billing Address
    ("address_line_1",   "Billing Address Line 1",               False, "billing",  ""),
    ("address_line_2",   "Billing Address Line 2",               False, "billing",  ""),
    ("city",             "Billing City",                         False, "billing",  ""),
    ("state",            "Billing State",                        False, "billing",  ""),
    ("postal_code",      "Billing Postal Code",                  False, "billing",  ""),
    ("country",          "Billing Country",                      False, "billing",  "2-letter code e.g. IN, US"),

    # Shipping Address
    ("shipping_address_line_1", "Shipping Address Line 1",       False, "shipping", ""),
    ("shipping_address_line_2", "Shipping Address Line 2",       False, "shipping", ""),
    ("shipping_city",           "Shipping City",                 False, "shipping", ""),
    ("shipping_state",          "Shipping State",                False, "shipping", ""),
    ("shipping_postal_code",    "Shipping Postal Code",          False, "shipping", ""),
    ("shipping_country",        "Shipping Country",              False, "shipping", "2-letter code e.g. IN, US"),
]

SECTION_LABELS = {
    "basic":     "Basic Information",
    "tax":       "GST & Tax Details",
    "financial": "Financial Details",
    "billing":   "Billing Address",
    "shipping":  "Shipping Address",
}

SECTIONS_ORDER = ["basic", "tax", "financial", "billing", "shipping"]


def get_fields_by_section():
    result = {}
    for key, label, required, section, notes in IMPORT_FIELDS:
        result.setdefault(section, []).append((key, label, required, notes))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# File parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv") or name.endswith(".tsv"):
        sep = "\t" if name.endswith(".tsv") else ","
        text = uploaded_file.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text), delimiter=sep)
        rows = list(reader)
        headers = list(reader.fieldnames or [])
        return headers, rows
    if name.endswith((".xlsx", ".xls")):
        if not HAS_OPENPYXL:
            raise ValueError("Install openpyxl: pip install openpyxl")
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return [], []
        headers = [str(h).strip() if h is not None else "" for h in all_rows[0]]
        rows = [{headers[i]: (str(v).strip() if v is not None else "")
                 for i, v in enumerate(r)} for r in all_rows[1:]]
        return headers, rows
    raise ValueError("Unsupported format. Use CSV, TSV, XLS, or XLSX.")


# ─────────────────────────────────────────────────────────────────────────────
# Auto-map  (same robust logic as item import)
# ─────────────────────────────────────────────────────────────────────────────

def _auto_map(headers):
    def _clean(s):
        s = re.sub(r'[\s_]*\([^)]*\)', '', s)
        return s.strip().lower().replace(" ", "_").replace("-", "_").strip("_")

    mapping = {}
    for h in headers:
        h_norm       = h.strip().lower().replace(" ", "_").replace("-", "_")
        h_norm_clean = _clean(h)
        for key, label, *_ in IMPORT_FIELDS:
            label_norm       = label.lower().replace(" ", "_")
            label_norm_clean = _clean(label)
            if (
                h_norm == key
                or h_norm == label_norm
                or h_norm_clean == key
                or h_norm_clean == label_norm_clean
            ):
                mapping[h] = key
                break
    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# Row validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_rows(rows, mapping):
    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: row.get(csv_h, "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []

        # Required: email
        email = mapped.get("email", "").strip()
        if not email:
            errors.append("Email is required")
        elif "@" not in email or "." not in email.split("@")[-1]:
            errors.append(f"Email format invalid (got: {email!r})")

        # Required: billing address fields
        for field, label in [
            ("address_line_1", "Billing Address Line 1"),
            ("city",           "Billing City"),
            ("state",          "Billing State"),
            ("postal_code",    "Billing Postal Code"),
        ]:
            if not mapped.get(field, "").strip():
                errors.append(f"{label} is required")

        # Required: country must be exactly 2 letters
        country = mapped.get("country", "").strip().upper()
        if not country:
            errors.append("Billing Country is required (2-letter code e.g. IN, US)")
        elif len(country) != 2:
            errors.append(
                f"Billing Country must be a 2-letter ISO code like 'IN' or 'US' "
                f"(got: {country!r})"
            )

        # Shipping country — only validate if provided
        s_country = mapped.get("shipping_country", "").strip().upper()
        if s_country and len(s_country) != 2:
            errors.append(
                f"Shipping Country must be a 2-letter ISO code like 'IN' or 'US' "
                f"(got: {s_country!r})"
            )

        # Vendor_type choices
        ct = mapped.get("vendor_type", "").lower()
        if ct and ct not in ("individual", "company"):
            errors.append(f"Vendor Type must be 'individual' or 'company' (got: {ct!r})")

        # tax_preference choices
        tp = mapped.get("tax_preference", "").lower()
        if tp and tp not in ("taxable", "tax_exempt"):
            errors.append(f"Tax Preference must be 'taxable' or 'tax_exempt' (got: {tp!r})")

        # opening_balance decimal
        ob = mapped.get("opening_balance", "")
        if ob:
            try:
                v = Decimal(ob)
                if v < 0:
                    errors.append(f"Opening Balance cannot be negative (got: {ob!r})")
            except InvalidOperation:
                errors.append(f"Opening Balance must be a number (got: {ob!r})")

        # Display name for skipped tab
        display = (
            mapped.get("email", "")
            or mapped.get("company_name", "")
            or f"{mapped.get('first_name', '')} {mapped.get('last_name', '')}".strip()
            or "—"
        )

        entry = {"row": row, "mapped": mapped, "errors": errors, "name": display}
        (skipped if errors else ready).append(entry)
    return ready, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Upload
# ─────────────────────────────────────────────────────────────────────────────

def import_vendors_step1(request, company_code):
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})
        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})

        request.session["cust_imp_headers"]   = headers
        request.session["cust_imp_rows"]      = rows
        request.session["cust_imp_filename"]  = uploaded.name
        request.session["cust_imp_duplicate"] = request.POST.get("duplicate_handling", "skip")
        request.session["cust_imp_row_count"] = len(rows)

        return redirect("import_vendors_step2", company_code=company_code)

    return render(request, "Purchase/vendor_import_step1.html", {"company_code": company_code})


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Map Fields
# ─────────────────────────────────────────────────────────────────────────────

def import_vendors_step2(request, company_code):
    headers = request.session.get("cust_imp_headers")
    if not headers:
        return redirect("import_vendors_step1", company_code=company_code)

    filename  = request.session.get("cust_imp_filename", "")
    row_count = request.session.get("cust_imp_row_count", 0)
    auto_map     = _auto_map(headers)
    auto_map_inv = {v: k for k, v in auto_map.items()}  # field_key → csv_header

    if request.method == "POST":
        mapping = {}
        for key, *_ in IMPORT_FIELDS:
            csv_h = request.POST.get(f"map_{key}", "").strip()
            if csv_h:
                mapping[csv_h] = key
        if not any(v == "email" for v in mapping.values()):
            messages.error(request, "You must map at least the 'Email' column.")
        else:
            request.session["cust_imp_mapping"] = mapping
            return redirect("import_vendors_step3", company_code=company_code)

    fields_by_section = get_fields_by_section()

    return render(request, "Purchase/vendor_import_step2.html", {
        "company_code":      company_code,
        "filename":          filename,
        "row_count":         row_count,
        "headers":           headers,
        "fields_by_section": fields_by_section,
        "sections_order":    SECTIONS_ORDER,
        "section_labels":    SECTION_LABELS,
        "auto_map_inv":      auto_map_inv,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 – Preview & Import
# ─────────────────────────────────────────────────────────────────────────────

def import_vendors_step3(request, company_code):
    headers   = request.session.get("cust_imp_headers")
    rows      = request.session.get("cust_imp_rows")
    mapping   = request.session.get("cust_imp_mapping")
    duplicate = request.session.get("cust_imp_duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect("import_vendors_step1", company_code=company_code)

    ready, skipped = _validate_rows(rows, mapping)

    # If duplicate handling is "skip", move rows with existing active emails to skipped
    if duplicate == "skip" and ready:
        from .models import Vendor
        from django.db.models.functions import Lower

        email_list = [
            entry["mapped"].get("email", "").strip().lower()
            for entry in ready
            if entry["mapped"].get("email", "").strip()
        ]
        email_set = set(email_list)

        if email_set:
            existing_active = set(
                Vendor.objects.filter(is_active=True)
                .annotate(email_l=Lower("email"))
                .filter(email_l__in=email_set)
                .values_list("email_l", flat=True)
            )

            if existing_active:
                remaining_ready = []
                for entry in ready:
                    em = entry["mapped"].get("email", "").strip().lower()
                    if em and em in existing_active:
                        entry["errors"].append("Email already exists ")
                        skipped.append(entry)
                    else:
                        remaining_ready.append(entry)
                ready = remaining_ready
    mapped_headers = set(mapping.keys())
    unmapped       = [h for h in headers if h not in mapped_headers]

    if request.method == "POST" and request.POST.get("action") == "import":
        from .models import Vendor, GstTreatment
        import re as _re
        from django.db.models import Max

        try:
            from PayTerms.models import PayTerms
        except ImportError:
            PayTerms = None

        created_count = 0
        updated_count = 0
        skipped_dup   = 0
        error_msgs    = []

        # ── Helpers (unchanged) ──────────────────────────────────────────────
        def to_bool(val, default=True):
            if not str(val).strip():
                return default
            return str(val).strip().lower() in ("true", "1", "yes", "y")

        def to_decimal(val, default=Decimal("0")):
            try:
                return Decimal(str(val).strip()) if str(val).strip() else default
            except InvalidOperation:
                return default

        def to_gst_treatment(raw_val):
            val = str(raw_val or "").strip()
            if not val:
                return None
            if val.isdigit():
                return GstTreatment.objects.filter(id=int(val)).first()
            return GstTreatment.objects.filter(name__iexact=val).first()

        def to_payment_terms(raw_val):
            if PayTerms is None:
                return None
            val = str(raw_val or "").strip()
            if not val:
                return None
            if val.isdigit():
                return PayTerms.objects.filter(id=int(val)).first()
            return PayTerms.objects.filter(name__iexact=val).first()

        # ── Pre-calculate starting vendor code ─────────────────────────────
        all_codes = Vendor.objects.values_list("vendor_code", flat=True)
        existing_nums = [
            int(n)
            for code in all_codes
            for n in _re.findall(r'\d+', code or "")
        ]
        code_counter = (max(existing_nums) + 1) if existing_nums else 1

        # ── Deduplicate emails within the file ───────────────────────────────
        seen_emails = set()
        deduped_ready = []
        for entry in ready:
            em = entry["mapped"].get("email", "").strip().lower()
            if em and em not in seen_emails:
                seen_emails.add(em)
                deduped_ready.append(entry)
            else:
                skipped_dup += 1

        # ── Main import loop ─────────────────────────────────────────────────
        for entry in deduped_ready:
            m     = entry["mapped"]
            email = m.get("email", "").strip()
            if not email:
                continue
            try:
                gst_treatment_obj = to_gst_treatment(m.get("gst_treatment", ""))
                pay_terms_obj     = to_payment_terms(m.get("payment_terms", ""))

                exists = Vendor.objects.filter(email__iexact=email).first()

                # If existing vendor is inactive, treat import as re-activation
                if exists and not exists.is_active:
                    obj = exists
                elif exists and duplicate == "skip":
                    skipped_dup += 1
                    continue
                else:
                    obj = exists or Vendor()

                # Basic
                obj.email         = email
                obj.vendor_type = m.get("vendor_type", "individual").lower() or "individual"
                obj.first_name    = m.get("first_name", "") or None
                obj.last_name     = m.get("last_name", "") or None
                obj.company_name  = m.get("company_name", "") or None
                obj.phone         = m.get("phone", "") or None
                obj.mobile        = m.get("mobile", "") or None
                obj.is_active     = to_bool(m.get("is_active", ""), default=True)
                obj.is_customer   = to_bool(m.get("is_customer", ""), default=False)

                # GST / Tax
                obj.gst_number       = m.get("gst_number", "") or None
                obj.pan_number       = m.get("pan_number", "") or None
                obj.tax_preference   = m.get("tax_preference", "taxable").lower() or "taxable"
                obj.exemption_reason = m.get("exemption_reason", "") or None
                obj.gst_treatment    = gst_treatment_obj

                # Financial
                obj.currency        = m.get("currency", "INR") or "INR"
                obj.payment_terms   = pay_terms_obj
                obj.opening_balance = to_decimal(m.get("opening_balance", ""), default=Decimal("0"))

                # Billing Address
                obj.address_line_1 = m.get("address_line_1", "")
                obj.address_line_2 = m.get("address_line_2", "") or None
                obj.city           = m.get("city", "")
                obj.state          = m.get("state", "")
                obj.postal_code    = m.get("postal_code", "")

                # Billing country — CountryField needs string, not None
                country_val = m.get("country", "").strip().upper()
                obj.country = country_val[:2] if country_val else "IN"

                # Shipping Address
                obj.shipping_address_line_1 = m.get("shipping_address_line_1", "") or None
                obj.shipping_address_line_2 = m.get("shipping_address_line_2", "") or None
                obj.shipping_city           = m.get("shipping_city", "") or None
                obj.shipping_state          = m.get("shipping_state", "") or None
                obj.shipping_postal_code    = m.get("shipping_postal_code", "") or None
                
                # Shipping country — CountryField: use "" instead of None when blank
                s_country = m.get("shipping_country", "").strip().upper()
                obj.shipping_country = s_country[:2] if len(s_country) == 2 else ""
                
                # Auto-generate vendor_code only for new records
                if not exists:
                    obj.vendor_code = f"CUST-{code_counter:04d}"
                    obj.id = None  # ← only for new records
                    code_counter += 1

                # Audit
                if request.user.is_authenticated:
                    if not exists:
                        obj.created_by = request.user
                    obj.updated_by = request.user


                # Validate before save to catch CountryField / model errors
                try:
                    obj.full_clean(exclude=["created_by", "updated_by", "payment_terms", 
                                            "gst_treatment", "created_at", "updated_at"])
                except Exception as validation_err:
                    error_msgs.append(f"Row '{email}': Validation failed — {validation_err}")
                    continue

                obj.save()

                # If vendor is also a Vendor, create/update customer with same details
                if obj.is_customer:
                    try:
                        from customer.models import Customer 
                    except Exception:
                        Customer = None

                    if Customer:
                        customer = Customer.objects.filter(email__iexact=obj.email).first()
                        if not customer:
                            customer = Customer()

                        customer.customer_code = obj.vendor_code
                        customer.customer_type = obj.vendor_type
                        customer.first_name = obj.first_name
                        customer.last_name = obj.last_name
                        customer.company_name = obj.company_name
                        customer.email = obj.email
                        customer.phone = obj.phone
                        customer.mobile = obj.mobile
                        customer.gst_number = obj.gst_number
                        customer.address_line_1 = obj.address_line_1
                        customer.address_line_2 = obj.address_line_2
                        customer.city = obj.city
                        customer.postal_code = obj.postal_code
                        customer.state = obj.state
                        customer.country = obj.country
                        customer.shipping_address_line_1 = obj.shipping_address_line_1
                        customer.shipping_address_line_2 = obj.shipping_address_line_2
                        customer.shipping_city = obj.shipping_city
                        customer.shipping_postal_code = obj.shipping_postal_code
                        customer.shipping_state = obj.shipping_state
                        customer.shipping_country = obj.shipping_country
                        customer.pan_number = obj.pan_number
                        customer.tax_preference = obj.tax_preference
                        customer.exemption_reason = obj.exemption_reason
                        customer.currency = obj.currency
                        customer.payment_terms = obj.payment_terms
                        customer.opening_balance = obj.opening_balance
                        customer.gst_treatment = obj.gst_treatment
                        customer.is_vendor = obj.is_customer
                        customer.is_active = obj.is_active
                        customer.created_at = obj.created_at
                        customer.updated_at = obj.updated_at
                        customer.created_by = obj.created_by
                        customer.updated_by = obj.updated_by
                        customer.save()

                if exists:
                    updated_count += 1
                else:
                    created_count += 1

            except Exception as exc:
                import traceback
                tb = traceback.format_exc()
                print(f"IMPORT ERROR for {email}: {exc}\n{tb}")   # shows in terminal
                error_msgs.append(f"Row '{email}': {exc} | {tb}")
        # ── Clear session ────────────────────────────────────────────────────
        for key in ("cust_imp_headers", "cust_imp_rows", "cust_imp_filename",
                    "cust_imp_mapping", "cust_imp_duplicate", "cust_imp_row_count"):
            request.session.pop(key, None)

        # ── Result messages ──────────────────────────────────────────────────
        if error_msgs:
            messages.warning(request,
                f"Import finished with errors: {created_count} created, "
                f"{updated_count} updated, {skipped_dup} skipped, "
                f"{len(error_msgs)} failed.")
            for msg in error_msgs:
                messages.warning(request, msg)
            # for msg in error_msgs[:5]:
            #     messages.warning(request, msg)
        else:
            messages.success(request,
                f"Import complete — {created_count} vendor(s) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        return redirect("vendor_list", company_code=company_code)

    return render(request, "Purchase/vendor_import_step3.html", {
        "company_code": company_code,
        "ready":        ready,
        "skipped":      skipped,
        "unmapped":     unmapped,
        "total":        len(rows),
        "duplicate":    duplicate,
        "mapping":      mapping,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Sample CSV download
# ─────────────────────────────────────────────────────────────────────────────

def import_vendors_sample(request, company_code):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_vendors.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in IMPORT_FIELDS])
    writer.writerow([
        # basic
        "company", "", "", "Acme Technologies Ltd", "billing@acmetech.com",
        "+91-9876543210", "+91-9876543210", "false",
        # tax
        "29ABCDE1234F1Z5", "ABCDE1234F", "taxable", "", "Registered Business",
        # financial
        "INR", "Net 30", "0",
        # billing
        "123 MG Road", "Suite 4B", "Bangalore", "Karnataka", "560001", "IN",
        # shipping
        "123 MG Road", "Suite 4B", "Bangalore", "Karnataka", "560001", "IN",
    ])
    writer.writerow([
        # basic
        "individual", "Ravi", "Kumar", "", "ravi.kumar@email.com",
        "+91-9123456789", "", "false",
        # tax
        "", "ABCFG5678H", "taxable", "", "",
        # financial
        "INR", "", "5000",
        # billing
        "45 Anna Salai", "", "Chennai", "Tamil Nadu", "600002", "IN",
        # shipping (same as billing)
        "45 Anna Salai", "", "Chennai", "Tamil Nadu", "600002", "IN",
    ])
    writer.writerow([
        # basic
        "company", "", "", "Global Exports Pvt Ltd", "accounts@globalexports.com",
        "+91-2212345678", "+91-9988776655", "false",
        # tax
        "27XYZAB9876C1Z3", "XYZAB9876C", "taxable", "", "SEZ Unit",
        # financial
        "USD", "Net 15", "25000",
        # billing
        "7 BKC Complex", "Tower B", "Mumbai", "Maharashtra", "400051", "IN",
        # shipping
        "Plot 5 MIDC", "", "Pune", "Maharashtra", "411018", "IN",
    ])
    return response


def export_vendors_csv(request, company_code):
    from .models import Vendor

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="vendors_export.csv"'
    writer = csv.writer(response)

    headers = [label for _, label, *_ in IMPORT_FIELDS]
    field_keys = [key for key, *_ in IMPORT_FIELDS]
    writer.writerow(headers)

    qs = (
        Vendor.objects.select_related("gst_treatment", "payment_terms")
        .filter(is_active=True)
        .order_by("id")
    )

    def _bool_str(val):
        return "true" if bool(val) else "false"

    for c in qs:
        row = []
        for key in field_keys:
            if key == "gst_treatment":
                row.append(c.gst_treatment.name if c.gst_treatment else "")
                continue
            if key == "payment_terms":
                row.append(c.payment_terms.name if c.payment_terms else "")
                continue
            if key == "is_active":
                row.append(_bool_str(c.is_active))
                continue
            if key == "is_customer":
                row.append(_bool_str(c.is_customer))
                continue

            val = getattr(c, key, "")
            if val is None:
                val = ""
            row.append(val)

        writer.writerow(row)

    return response

