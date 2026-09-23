"""
Subcategory Import Wizard – import_subcategory_views.py
Mapped exactly to your Subcategory model fields.
Place in category/import_subcategory_views.py
"""

import csv
import io
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ─────────────────────────────────────────────────────────────────────────────
# CSV column label  →  what it maps to in your Subcategory model
# Format: (csv_key, display_label, required, section, model_field_or_None)
#   model_field = None means it needs special handling (FK, boolean, etc.)
# ─────────────────────────────────────────────────────────────────────────────
IMPORT_FIELDS = [
    # Basic
    ("category_name",     "Category Name",     True,  "basic", None),
    ("subcategory_name",  "Subcategory Name",  True,  "basic", "subcategory_name"),
]

SECTION_LABELS = {
    "basic": "Basic Details",
}

SECTIONS_ORDER = ["basic"]

# Group fields by section for the template
def get_fields_by_section():
    result = {}
    for key, label, required, section, model_field in IMPORT_FIELDS:
        result.setdefault(section, []).append((key, label, required))
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


def _auto_map(headers):
    """Map CSV headers → IMPORT_FIELDS keys by fuzzy matching."""
    mapping = {}
    for h in headers:
        h_norm = h.strip().lower().replace(" ", "_").replace("-", "_")
        for key, label, *_ in IMPORT_FIELDS:
            if h_norm == key or h_norm == label.lower().replace(" ", "_") or h_norm.startswith(key):
                mapping[h] = key
                break
    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# Row validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_rows(rows, mapping):
    """mapping: {csv_header: field_key}"""
    from .models import Category

    # Build a case-insensitive lookup of existing categories once, up front.
    category_by_name = {c.category_name.strip().lower(): c
                         for c in Category.objects.filter(status=True)
                         if c.category_name}

    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: row.get(csv_h, "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []

        cat_name = mapped.get("category_name", "").strip()
        sub_name = mapped.get("subcategory_name", "").strip()

        if not sub_name:
            errors.append("Subcategory Name is required")
        if not cat_name:
            errors.append("Category Name is required")

        category_obj = None
        if cat_name:
            category_obj = category_by_name.get(cat_name.lower())
            if category_obj is None:
                errors.append(f"Category '{cat_name}' does not exist")

        entry = {
            "row": row, "mapped": mapped, "errors": errors,
            "name": sub_name or "-",
            "category_obj": category_obj,
        }
        (skipped if errors else ready).append(entry)
    return ready, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Configure & Upload
# ─────────────────────────────────────────────────────────────────────────────

def import_subcategory_step1(request, company_code):
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "import_subcategory_step1.html", {"company_code": company_code})

        request.session["imp_sub_headers"]   = headers
        request.session["imp_sub_rows"]      = rows
        request.session["imp_sub_filename"]  = uploaded.name
        request.session["imp_sub_duplicate"] = request.POST.get("duplicate_handling", "skip")
        request.session["imp_sub_row_count"] = len(rows)

        return redirect("import_subcategory_step2", company_code=company_code)

    return render(request, "import_subcategory_step1.html", {"company_code": company_code})


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Map Fields
# ─────────────────────────────────────────────────────────────────────────────

def import_subcategory_step2(request, company_code):
    headers = request.session.get("imp_sub_headers")
    if not headers:
        return redirect("import_subcategory_step1", company_code=company_code)

    filename     = request.session.get("imp_sub_filename", "")
    row_count    = request.session.get("imp_sub_row_count", 0)
    auto_map     = _auto_map(headers)         # csv_header → field_key
    auto_map_inv = {v: k for k, v in auto_map.items()}  # field_key → csv_header

    if request.method == "POST":
        mapping = {}
        for key, *_ in IMPORT_FIELDS:
            csv_h = request.POST.get(f"map_{key}", "").strip()
            if csv_h:
                mapping[csv_h] = key

        mapped_keys = set(mapping.values())
        if "subcategory_name" not in mapped_keys or "category_name" not in mapped_keys:
            messages.error(request, "You must map both 'Category Name' and 'Subcategory Name' columns.")
            # fall through to re-render
        else:
            request.session["imp_sub_mapping"] = mapping
            return redirect("import_subcategory_step3", company_code=company_code)

    fields_by_section = get_fields_by_section()

    return render(request, "import_subcategory_step2.html", {
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

def import_subcategory_step3(request, company_code):
    headers   = request.session.get("imp_sub_headers")
    rows      = request.session.get("imp_sub_rows")
    mapping   = request.session.get("imp_sub_mapping")
    duplicate = request.session.get("imp_sub_duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect("import_subcategory_step1", company_code=company_code)

    ready, skipped = _validate_rows(rows, mapping)
    mapped_headers = set(mapping.keys())
    unmapped       = [h for h in headers if h not in mapped_headers]

    # If duplicates are set to be skipped, show them in the skipped preview
    if duplicate == "skip" and ready:
        from .models import Subcategory

        pairs = [(e["category_obj"].pk, e["mapped"].get("subcategory_name", "").strip().lower())
                 for e in ready if e.get("category_obj")]
        if pairs:
            cat_ids = {p[0] for p in pairs}
            existing_pairs = set(
                Subcategory.objects.filter(status=True, category_id__in=cat_ids)
                .values_list("category_id", "subcategory_name")
            )
            existing_lookup = {(cid, name.strip().lower()) for cid, name in existing_pairs}

            next_ready = []
            for entry in ready:
                cat_obj = entry.get("category_obj")
                name = entry["mapped"].get("subcategory_name", "").strip()
                key = (cat_obj.pk, name.lower()) if cat_obj else None
                if key and key in existing_lookup:
                    entry = dict(entry)
                    entry["errors"] = entry.get("errors", []) + ["Duplicate subcategory exists in this category (will be skipped)"]
                    skipped.append(entry)
                else:
                    next_ready.append(entry)
            ready = next_ready

    if request.method == "POST" and request.POST.get("action") == "import":
        from Lyraerp.utils.redirect_utils import redirect_with_company
        from .models import Subcategory

        created_count = 0
        updated_count = 0
        skipped_dup   = 0
        error_msgs    = []

        for entry in ready:
            m         = entry["mapped"]
            name      = m.get("subcategory_name", "").strip()
            category  = entry.get("category_obj")
            if not name or not category:
                continue
            try:
                exists = Subcategory.objects.filter(
                    category=category, subcategory_name__iexact=name
                ).first()

                if exists and duplicate == "skip":
                    if exists.status:
                        skipped_dup += 1
                        continue

                obj = exists or Subcategory()
                obj.category = category
                obj.subcategory_name = name
                obj.status = True

                if request.user.is_authenticated:
                    if not exists:
                        obj.created_by = request.user
                    obj.updated_by = request.user

                obj.save()

                if exists:
                    updated_count += 1
                else:
                    created_count += 1

            except Exception as exc:
                error_msgs.append(f"Row '{name}': {exc}")

        # Clear session
        for key in ("imp_sub_headers", "imp_sub_rows", "imp_sub_filename",
                    "imp_sub_mapping", "imp_sub_duplicate", "imp_sub_row_count"):
            request.session.pop(key, None)

        if error_msgs:
            messages.warning(request,
                f"Import finished with errors: {created_count} created, "
                f"{updated_count} updated, {skipped_dup} skipped, "
                f"{len(error_msgs)} failed.")
            for msg in error_msgs[:5]:
                messages.warning(request, msg)
        else:
            messages.success(request,
                f"Import complete - {created_count} subcategory(s) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        return redirect_with_company("subcategory_list")

    return render(request, "import_subcategory_step3.html", {
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

def import_subcategory_sample(request, company_code):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_subcategory.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in IMPORT_FIELDS])
    writer.writerow(["Groceries", "Dairy"])
    writer.writerow(["Electronics", "Mobile Phones"])
    return response
