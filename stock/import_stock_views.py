"""
Stock Import Wizard – import_stock_views.py
Mapped exactly to your Stock model fields.
Place in Items/import_stock_views.py
"""

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ─────────────────────────────────────────────────────────────────────────────
# CSV column label  →  what it maps to in your Item model
# Format: (csv_key, display_label, required, section, model_field_or_None)
#   model_field = None means it needs special handling (FK, boolean, etc.)
# ─────────────────────────────────────────────────────────────────────────────
IMPORT_FIELDS = [
    # Basic
    ("quantity",         "Quantity",         True,  "basic", "quantity"),
    ("expiration_date",  "Expiration Date",  False, "basic", "expiration_date"),
    ("item_name",        "Item Name",        True,  "basic", None),
    ("warehouse_name",   "Warehouse Name",   True,  "basic", None),
]

SECTION_LABELS = {
    "basic":     "Basic Details",
    
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
            label_norm = label.lower().replace(" ", "_").split("_")[0]  # first word
            if h_norm == key or h_norm == label.lower().replace(" ", "_") or h_norm.startswith(key):
                mapping[h] = key
                break
    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# Row validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_rows(rows, mapping):
    """mapping: {csv_header: field_key}"""
    from Items.models import Item
    from warehouse.models import Warehouse

    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: row.get(csv_h, "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []
        quantity_raw = mapped.get("quantity", "").strip()
        item_name_raw = mapped.get("item_name", "").strip()
        warehouse_name_raw = mapped.get("warehouse_name", "").strip()
        expiration_raw = mapped.get("expiration_date", "").strip()

        if not quantity_raw:
            errors.append("Quantity is required")
        else:
            try:
                Decimal(quantity_raw)
            except InvalidOperation:
                errors.append("Quantity must be a valid number")

        item_obj = None
        if not item_name_raw:
            errors.append("Item Name is required")
        else:
            item_qs = Item.objects.filter(name__iexact=item_name_raw, status=True)
            if not item_qs.exists():
                errors.append(f"Item Name '{item_name_raw}' not found")
            elif item_qs.count() > 1:
                errors.append(f"Item Name '{item_name_raw}' is not unique")
            else:
                item_obj = item_qs.first()

        warehouse_obj = None
        if not warehouse_name_raw:
            errors.append("Warehouse Name is required")
        else:
            warehouse_qs = Warehouse.objects.filter(warehouse_name__iexact=warehouse_name_raw, status=True)
            if not warehouse_qs.exists():
                errors.append(f"Warehouse Name '{warehouse_name_raw}' not found")
            elif warehouse_qs.count() > 1:
                errors.append(f"Warehouse Name '{warehouse_name_raw}' is not unique")
            else:
                warehouse_obj = warehouse_qs.first()

        if expiration_raw:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expiration_raw):
                try:
                    datetime.strptime(expiration_raw, "%Y-%m-%d")
                except ValueError:
                    errors.append("Expiration Date must be in YYYY-MM-DD or DD-MM-YYYY format")
            elif re.fullmatch(r"\d{2}-\d{2}-\d{4}", expiration_raw):
                try:
                    parsed = datetime.strptime(expiration_raw, "%d-%m-%Y").date()
                    # Normalize to YYYY-MM-DD for downstream parsing.
                    mapped["expiration_date"] = parsed.strftime("%Y-%m-%d")
                except ValueError:
                    errors.append("Expiration Date must be in YYYY-MM-DD or DD-MM-YYYY format")
            else:
                errors.append("Expiration Date must be in YYYY-MM-DD or DD-MM-YYYY format")

        if item_obj:
            mapped["item_id"] = item_obj.id
        if warehouse_obj:
            mapped["warehouse_id"] = warehouse_obj.id

        name = f"{item_name_raw or '-'} / {warehouse_name_raw or '-'}"

        entry = {"row": row, "mapped": mapped, "errors": errors,
                 "name": name or "-"}
        (skipped if errors else ready).append(entry)
    return ready, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Configure & Upload
# ─────────────────────────────────────────────────────────────────────────────

def import_stock_step1(request, company_code):
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "import_stock_step1.html", {"company_code": company_code})

        request.session["imp_headers"]   = headers
        request.session["imp_rows"]      = rows
        request.session["imp_filename"]  = uploaded.name
        request.session["imp_duplicate"] = request.POST.get("duplicate_handling", "skip")
        request.session["imp_row_count"] = len(rows)

        return redirect("import_stock_step2", company_code=company_code)

    return render(request, "import_stock_step1.html", {"company_code": company_code})


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Map Fields
# ─────────────────────────────────────────────────────────────────────────────

def import_stock_step2(request, company_code):
    headers = request.session.get("imp_headers")
    if not headers:
        return redirect("import_stock_step1", company_code=company_code)

    filename     = request.session.get("imp_filename", "")
    row_count    = request.session.get("imp_row_count", 0)
    auto_map     = _auto_map(headers)         # csv_header → field_key
    auto_map_inv = {v: k for k, v in auto_map.items()}  # field_key → csv_header

    if request.method == "POST":
        mapping = {}
        for key, *_ in IMPORT_FIELDS:
            csv_h = request.POST.get(f"map_{key}", "").strip()
            if csv_h:
                mapping[csv_h] = key
        required_keys = {"quantity", "item_name", "warehouse_name"}
        if not required_keys.issubset(set(mapping.values())):
            messages.error(request, "You must map 'Quantity', 'Item Name', and 'Warehouse Name'.")
            # fall through to re-render
        else:
            request.session["imp_mapping"] = mapping
            return redirect("import_stock_step3", company_code=company_code)

    fields_by_section = get_fields_by_section()

    return render(request, "import_stock_step2.html", {
        "company_code":    company_code,
        "filename":        filename,
        "row_count":       row_count,
        "headers":         headers,
        "fields_by_section": fields_by_section,
        "sections_order":  SECTIONS_ORDER,
        "section_labels":  SECTION_LABELS,
        "auto_map_inv":    auto_map_inv,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 – Preview & Import
# ─────────────────────────────────────────────────────────────────────────────

def import_stock_step3(request, company_code):
    headers   = request.session.get("imp_headers")
    rows      = request.session.get("imp_rows")
    mapping   = request.session.get("imp_mapping")
    duplicate = request.session.get("imp_duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect("import_stock_step1", company_code=company_code)

    ready, skipped = _validate_rows(rows, mapping)
    mapped_headers = set(mapping.keys())
    unmapped       = [h for h in headers if h not in mapped_headers]

    # If duplicates are set to be skipped, show them in the skipped preview
    if duplicate == "skip" and ready:
        from .models import Stock

        next_ready = []
        for entry in ready:
            item_id_val = entry["mapped"].get("item_id")
            warehouse_id_val = entry["mapped"].get("warehouse_id")
            exp_raw = entry["mapped"].get("expiration_date", "").strip()
            exp_date = None
            if exp_raw:
                try:
                    exp_date = datetime.strptime(exp_raw, "%Y-%m-%d").date()
                except ValueError:
                    exp_date = None

            if item_id_val and warehouse_id_val:
                exists = Stock.objects.filter(
                    item_id=item_id_val,
                    warehouse_id=warehouse_id_val,
                    expiration_date=exp_date,
                    status=True
                ).exists()
                if exists:
                    entry = dict(entry)
                    entry["errors"] = entry.get("errors", []) + ["Duplicate stock exists (will be skipped)"]
                    skipped.append(entry)
                    continue

            next_ready.append(entry)

        ready = next_ready

    if request.method == "POST" and request.POST.get("action") == "import":
        from Lyraerp.utils.redirect_utils import redirect_with_company
        from .models import Stock

        created_count = 0
        updated_count = 0
        skipped_dup   = 0
        error_msgs    = []

        for entry in ready:
            m    = entry["mapped"]
            quantity_raw = m.get("quantity", "").strip()
            item_id_val = m.get("item_id")
            warehouse_id_val = m.get("warehouse_id")
            exp_raw = m.get("expiration_date", "").strip()

            if not quantity_raw or not item_id_val or not warehouse_id_val:
                continue

            try:
                quantity_val = Decimal(quantity_raw)
            except InvalidOperation:
                continue

            exp_date = None
            if exp_raw:
                try:
                    exp_date = datetime.strptime(exp_raw, "%Y-%m-%d").date()
                except ValueError:
                    exp_date = None
            try:
                exists = Stock.objects.filter(
                    item_id=item_id_val,
                    warehouse_id=warehouse_id_val,
                    expiration_date=exp_date,
                ).first()

                if exists and duplicate == "skip":
                    if exists.status:
                        skipped_dup += 1
                        continue

                obj = exists or Stock()
                obj.quantity = quantity_val
                obj.expiration_date = exp_date
                obj.item_id = item_id_val
                obj.warehouse_id = warehouse_id_val
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
                item_name_raw = m.get("item_name", "")
                warehouse_name_raw = m.get("warehouse_name", "")
                error_msgs.append(f"Row '{item_name_raw} / {warehouse_name_raw}': {exc}")

        # Clear session
        for key in ("imp_headers", "imp_rows", "imp_filename",
                    "imp_mapping", "imp_duplicate", "imp_row_count"):
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
                f"Import complete - {created_count} stock(s) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        return redirect_with_company("stock_list")

    return render(request, "import_stock_step3.html", {
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

def import_stock_sample(request, company_code):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_stocks.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in IMPORT_FIELDS])
    writer.writerow([
        "100.00",
        "2026-12-31",
        "Sample Item",
        "Main Warehouse",
    ])
    writer.writerow([
        "25.50",
        "",
        "Second Item",
        "Main Warehouse",
    ])
    return response
