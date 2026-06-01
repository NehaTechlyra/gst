"""
Item Import Wizard – import_views.py
Mapped exactly to your Item model fields.
Place in Items/import_views.py
"""

import csv
import io
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
# CSV column label  →  what it maps to in your Item model
# Format: (csv_key, display_label, required, section, model_field_or_None)
#   model_field = None means it needs special handling (FK, boolean, etc.)
# ─────────────────────────────────────────────────────────────────────────────
IMPORT_FIELDS = [
    # Basic
    ("name",             "Item Name",              True,  "basic",    "name"),
    ("type",             "Type (goods/service)",   False, "basic",    "type"),
    ("unit",             "Unit",                   False, "basic",    "unit"),
    ("brand",            "Brand",                  False, "basic",    None),   # FK
    ("category",         "Category",               False, "basic",    None),   # FK
    ("item_type",         "Item Type",                   False, "basic",    None),   # FK

    ("hsn_code",         "HSN Code",               False, "basic",    "hsn_code"),
    ("sac_code",             "SAC Code",                           False, "basic",     "sac_code"),
    ("barcode",              "Barcode",                            False, "inventory", None),   # FK lookup
    # ("status",           "Status (true/false)",    False, "basic",    None),   # bool

    # Sales
    ("selling_price",    "Selling Price",          False, "sales",    "selling_price"),
    ("sales_account",    "Sales Account",          False, "sales",    "sales_account"),
    ("sales_desc",       "Sales Description",      False, "sales",    "sales_desc"),
    ("taxincld_slprice",     "Tax Included in Selling Price (true/false)", False, "sales", None),  # bool

    # Purchase
    ("cost_price",       "Cost Price",             False, "purchase", "cost_price"),
    ("purchase_account", "Purchase Account",       False, "purchase", "purchase_account"),
    ("purchase_desc",    "Purchase Description",   False, "purchase", "purchase_desc"),
    ("taxincld_costprice",   "Tax Included in Cost Price (true/false)", False, "purchase", None),  # bool
    ("preferred_vendor",     "Preferred Vendor",                   False, "purchase",  None),   # FK lookup by name

    # Tax
    ("tax_pref",         "Tax Preference (taxable/non_taxable)", False, "tax", "tax_pref"),
    ("intra_tax",            "Intra State Tax (TaxGroup name/rate)", False, "tax",       None),   # FK
    ("inter_tax_group",      "Inter State Tax (Tax name/rate)",      False, "tax",       None),   # FK

    # Inventory
    ("track_inventory",  "Track Inventory (true/false)", False, "inventory", None),  # bool
    ("op_stock",         "Opening Stock",          False, "inventory", "op_stock"),
    ("op_rate",          "Opening Stock Rate",     False, "inventory", "op_rate"),
    ("inv_method",       "Valuation Method (FIFO/WAC)", False, "inventory", "inv_method"),
    ("inv_acc",              "Inventory Account",                  False, "inventory", "inv_acc"),

    ("min_stock",            "Minimum Stock Level",                False, "basic",     "min_stock"),

]

SECTION_LABELS = {
    "basic":     "Basic Details",
    "sales":     "Sales Information",
    "purchase":  "Purchase Information",
    "tax":       "Tax Details",
    "inventory": "Inventory Details",
}

SECTIONS_ORDER = ["basic", "sales", "purchase", "tax", "inventory"]

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
    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: (row.get(csv_h) or "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []
        name = mapped.get("name", "").strip()
        if not name:
            errors.append("Item Name is required")
        # Validate decimal fields
        for dec_field in ("selling_price", "cost_price", "op_stock", "op_rate", "min_stock"):
            val = mapped.get(dec_field, "")
            if val:
                try:
                    Decimal(val)
                except InvalidOperation:
                    errors.append(f"{dec_field} must be a number (got: {val!r})")
        
        # Integer fields
        for int_field in ("sac_code",):
            val = mapped.get(int_field, "")
            if val and not val.isdigit():
                errors.append(f"{int_field} must be an integer (got: {val!r})")
        
        # Validate type choices
        type_val = mapped.get("type", "").lower()
        if type_val and type_val not in ("goods", "service"):
            errors.append(f"Type must be 'goods' or 'service' (got: {type_val!r})")
        
        # Validate tax_pref
        tp = mapped.get("tax_pref", "").lower()
        if tp and tp not in ("taxable", "non_taxable"):
            errors.append(f"Tax Preference must be 'taxable' or 'non_taxable' (got: {tp!r})")

        # Inv method choices
        inv = mapped.get("inv_method", "").upper()
        if inv and inv not in ("FIFO", "WAC"):
            errors.append(f"Valuation Method must be 'FIFO' or 'WAC' (got: {inv!r})")

        entry = {"row": row, "mapped": mapped, "errors": errors,
                 "name": name or "—"}
        (skipped if errors else ready).append(entry)
    return ready, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Configure & Upload
# ─────────────────────────────────────────────────────────────────────────────

def import_items_step1(request, company_code):
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "import_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "import_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "import_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "import_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "import_step1.html", {"company_code": company_code})

        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "import_step1.html", {"company_code": company_code})

        request.session["imp_headers"]   = headers
        request.session["imp_rows"]      = rows
        request.session["imp_filename"]  = uploaded.name
        request.session["imp_duplicate"] = request.POST.get("duplicate_handling", "skip")
        request.session["imp_row_count"] = len(rows)

        return redirect("import_items_step2", company_code=company_code)

    return render(request, "import_step1.html", {"company_code": company_code})


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Map Fields
# ─────────────────────────────────────────────────────────────────────────────

def import_items_step2(request, company_code):
    headers = request.session.get("imp_headers")
    if not headers:
        return redirect("import_items_step1", company_code=company_code)

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
        if not any(v == "name" for v in mapping.values()):
            messages.error(request, "You must map at least the 'Item Name' column.")
            # fall through to re-render
        else:
            request.session["imp_mapping"] = mapping
            return redirect("import_items_step3", company_code=company_code)

    fields_by_section = get_fields_by_section()

    return render(request, "import_step2.html", {
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

def import_items_step3(request, company_code):
    headers   = request.session.get("imp_headers")
    rows      = request.session.get("imp_rows")
    mapping   = request.session.get("imp_mapping")
    duplicate = request.session.get("imp_duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect("import_items_step1", company_code=company_code)

    ready, skipped = _validate_rows(rows, mapping)
    mapped_headers = set(mapping.keys())
    unmapped       = [h for h in headers if h not in mapped_headers]

    if request.method == "POST" and request.POST.get("action") == "import":
        from Items.models import Item
        from unit.models import Unit
        from brand.models import Brand
        from category.models import Category
        from type.models import Type





        # ── Import these lazily to avoid circular issues ──
        try:
            from Purchase.models import Vendor
        except ImportError:
            Vendor = None

        try:
            from Tax.models import TaxGroup, Tax
        except ImportError:
            TaxGroup = None
            Tax = None

        try:
            from Items.models import Barcode
        except ImportError:
            Barcode = None

        created_count = 0
        updated_count = 0
        skipped_dup   = 0
        error_msgs    = []
        created_units = set()
        created_brands = set()
        
        created_types = set()
        created_categories = set()
        missing_vendors = set()
        vendor_display_map = None

        # ── Helpers ──────────────────────────────────────────────────────────

        def to_bool(val):
            return str(val).strip().lower() in ("true", "1", "yes", "y")

        def to_decimal(val):
            try:
                return Decimal(str(val).strip()) if val else None
            except InvalidOperation:
                return None
        def to_int(val):
            try:
                return int(str(val).strip()) if val else None
            except (ValueError, TypeError):
                return None

        def to_unit_id(raw_val):
            """
            Resolve CSV unit values to Unit.id (stored as string in Item.unit).
            Accepts either a numeric id or a unit name like "pcs"/"hrs".
            If a unit name does not exist, create it.
            """
            val = str(raw_val or "").strip()
            if not val:
                default_unit = Unit.objects.filter(unit_name__iexact="pcs", status=True).first()
                if not default_unit:
                    default_unit = Unit.objects.filter(unit_name__iexact="pcs").first()
                if default_unit:
                    return str(default_unit.id)
                default_unit = Unit.objects.create(unit_name="pcs", status=True)
                created_units.add(default_unit.unit_name)
                return str(default_unit.id)

            if val.isdigit():
                return val

            unit_obj = Unit.objects.filter(unit_name__iexact=val, status=True).first()
            if not unit_obj:
                unit_obj = Unit.objects.filter(unit_name__iexact=val).first()
            if unit_obj:
                return str(unit_obj.id)

            unit_obj = Unit.objects.create(unit_name=val, status=True)
            created_units.add(unit_obj.unit_name)
            return str(unit_obj.id)

        def to_brand_obj(raw_val):
            """
            Resolve CSV brand values to Brand instance.
            Accepts either a numeric id or a brand name.
            If a brand name does not exist, create it.
            """
            val = str(raw_val or "").strip()
            if not val:
                return None

            if val.isdigit():
                brand_obj = Brand.objects.filter(id=int(val)).first()
                if brand_obj:
                    return brand_obj

            brand_obj = Brand.objects.filter(brand_name__iexact=val, status=True).first()
            if not brand_obj:
                brand_obj = Brand.objects.filter(brand_name__iexact=val).first()
            if brand_obj:
                return brand_obj

            create_kwargs = {"brand_name": val, "status": True}
            if request.user.is_authenticated:
                create_kwargs["created_by"] = request.user
                create_kwargs["updated_by"] = request.user
            brand_obj = Brand.objects.create(**create_kwargs)
            created_brands.add(brand_obj.brand_name)
            print(f"Created new brand: {brand_obj.brand_name} (id: {brand_obj.id})")
            return brand_obj
        
        def to_category_obj(raw_val):
            """
            Resolve CSV category values to Category instance.
            Accepts either a numeric id or a category name.
            If a category name does not exist, create it.
            """
            val = str(raw_val or "").strip()
            if not val:
                return None

            if val.isdigit():
                category_obj = Category.objects.filter(id=int(val)).first()
                if category_obj:
                    return category_obj

            category_obj = Category.objects.filter(category_name__iexact=val, status=True).first()
            if not category_obj:
                category_obj = Category.objects.filter(category_name__iexact=val).first()
            if category_obj:
                return category_obj

            create_kwargs = {"category_name": val, "status": True}
            if request.user.is_authenticated:
                create_kwargs["created_by"] = request.user
                create_kwargs["updated_by"] = request.user
            category_obj = Category.objects.create(**create_kwargs)
            created_categories.add(category_obj.category_name)
            print(f"Created new category: {category_obj.category_name} (id: {category_obj.id})")
            return category_obj
        
        def to_type_obj(raw_val):
            """
            Resolve CSV type values to Type instance.
            Accepts either a numeric id or a type name.
            If a type name does not exist, create it.
            """
            val = str(raw_val or "").strip()
            if not val:
                return None

            if val.isdigit():
                type_obj = Type.objects.filter(id=int(val)).first()
                if type_obj:
                    return type_obj

            type_obj = Type.objects.filter(type_name__iexact=val, status=True).first()
            if not type_obj:
                type_obj = Type.objects.filter(type_name__iexact=val).first()
            if type_obj:
                return type_obj

            create_kwargs = {"type_name": val, "status": True}
            if request.user.is_authenticated:
                create_kwargs["created_by"] = request.user
                create_kwargs["updated_by"] = request.user
            type_obj = Type.objects.create(**create_kwargs)
            created_types.add(type_obj.type_name)
            print(f"Created new type: {type_obj.type_name} (id: {type_obj.id})")
            return type_obj
        
        def to_vendor_obj(raw_val):
            """
            Resolve vendor name/id → Vendor instance.
            If not found by name, skip (return None) — do NOT create.
            """
            if Vendor is None:
                return None
            val = str(raw_val or "").strip()
            if not val:
                return None

            if val.isdigit():
                vendor_obj = Vendor.objects.filter(id=int(val)).first()
                if vendor_obj:
                    return vendor_obj
            print("preferred vendor lookup fallback for:", val)
            # Try common name fields — adjust field names to match your Vendor model
            vendor_obj = (
                Vendor.objects.filter(email__iexact=val).first()
                or Vendor.objects.filter(vendor_code__iexact=val).first()
            )
            if vendor_obj:
                return vendor_obj

            nonlocal vendor_display_map
            if vendor_display_map is None:
                vendor_display_map = {}
                for candidate in Vendor.objects.all():
                    display_name = str(candidate).strip().lower()
                    if display_name:
                        vendor_display_map.setdefault(display_name, candidate)

            vendor_obj = vendor_display_map.get(val.lower())
            if vendor_obj:
                return vendor_obj

            missing_vendors.add(val)
            return None

        def to_taxgroup_obj(raw_val):
            """
            Resolve intra_tax → TaxGroup instance.
            Accepts: group_name (e.g. "GST 18%")  OR  rate as number (e.g. "18")
            """
            if TaxGroup is None:
                return None
            val = str(raw_val or "").strip()
            if not val:
                return None

            # Try exact name match first
            obj = TaxGroup.objects.filter(group_name__iexact=val).first()
            if obj:
                return obj

            # Try matching by rate — find a TaxGroup whose member taxes sum/match this rate
            try:
                rate = Decimal(val)
                # Match TaxGroups that contain at least one Tax with this rate
                obj = TaxGroup.objects.filter(taxes__rate=rate).distinct().first()
                if obj:
                    return obj
            except InvalidOperation:
                pass

            return None

        def to_tax_obj(raw_val):
            """
            Resolve inter_tax_group → Tax instance.
            Accepts: taxname (e.g. "IGST 18%")  OR  rate as number (e.g. "18")
            """
            if Tax is None:
                return None
            val = str(raw_val or "").strip()
            if not val:
                return None

            # Try exact name match first
            obj = Tax.objects.filter(taxname__iexact=val).first()
            if obj:
                return obj

            # Try matching by rate
            try:
                rate = Decimal(val)
                obj = Tax.objects.filter(rate=rate).first()
                if obj:
                    return obj
            except InvalidOperation:
                pass

            return None

        def to_barcode_obj(raw_val):
            """
            Resolve barcode value → Barcode instance or None.
            Looks up by barcode number/code field. Does NOT create.
            """
            if Barcode is None:
                return None
            val = str(raw_val or "").strip()
            if not val:
                return None
            if val.isdigit():
                obj = Barcode.objects.filter(id=int(val)).first()
                if obj:
                    return obj
            return (
                Barcode.objects.filter(barcode__iexact=val).first()
                or Barcode.objects.filter(code__iexact=val).first()
                or Barcode.objects.filter(barcode_number__iexact=val).first()
            )


        # ── Main import loop ─────────────────────────────────────────────────

        for entry in ready:
            m    = entry["mapped"]
            name = m.get("name", "").strip()
            if not name:
                continue
            try:
                brand_obj = to_brand_obj(m.get("brand", ""))
                category_obj = to_category_obj(m.get("category", ""))
                type_obj = to_type_obj(m.get("item_type", ""))

                vendor_raw = m.get("preferred_vendor", "")
                vendor_obj = to_vendor_obj(vendor_raw)
                intra_obj  = to_taxgroup_obj(m.get("intra_tax", ""))
                inter_obj  = to_tax_obj(m.get("inter_tax_group", ""))
                barcode_obj = to_barcode_obj(m.get("barcode", ""))
                exists = Item.objects.filter(name__iexact=name).first()
                existing_preferred_vendor = exists.preferred_vendor if exists else None

                if exists and duplicate == "skip":
                    skipped_dup += 1
                    continue

                obj = exists or Item()

                # ── Basic ────────────────────────────────────────────────────
                obj.name             = name
                obj.type             = m.get("type", "goods").lower() or "goods"
                obj.unit             = to_unit_id(m.get("unit", ""))
                obj.brand            = brand_obj
                obj.item_type        = type_obj
                obj.category         = category_obj

                obj.hsn_code         = m.get("hsn_code", "") or None
                obj.status   = to_bool(m["status"]) if m.get("status") else (obj.status if exists else True)

                sac = to_int(m.get("sac_code", ""))
                if sac is not None:
                    obj.sac_code = sac

                min_s = to_decimal(m.get("min_stock", ""))
                if min_s is not None:
                    obj.min_stock = min_s

                # ── Sales ────────────────────────────────────────────────────
                obj.sales_account    = m.get("sales_account", "") or None
                obj.sales_desc       = m.get("sales_desc", "") or None
                sp = to_decimal(m.get("selling_price", ""))
                
                if sp is not None:
                    obj.selling_price = sp
                
                if m.get("taxincld_slprice", ""):
                    obj.taxincld_slprice = to_bool(m["taxincld_slprice"])
                
                # ── Purchase ─────────────────────────────────────────────────
                obj.purchase_account = m.get("purchase_account", "") or None
                obj.purchase_desc    = m.get("purchase_desc", "") or None
                if vendor_raw.strip():
                    if vendor_obj is not None:
                        obj.preferred_vendor = vendor_obj
                    elif existing_preferred_vendor is not None:
                        obj.preferred_vendor = existing_preferred_vendor
                elif not exists:
                    obj.preferred_vendor = None

                cp = to_decimal(m.get("cost_price", ""))
                if cp is not None:
                    obj.cost_price = cp

                if m.get("taxincld_costprice", ""):
                    obj.taxincld_costprice = to_bool(m["taxincld_costprice"])
                


                # ── Tax ──────────────────────────────────────────────────────
                obj.tax_pref         = m.get("tax_pref", "taxable").lower() or "taxable"

                if intra_obj is not None:
                    obj.intra_tax = intra_obj
                if inter_obj is not None:
                    obj.inter_tax_group = inter_obj


                # ── Inventory ────────────────────────────────────────────────
                if m.get("track_inventory", ""):
                    obj.track_inventory = to_bool(m["track_inventory"])
                
                ops = to_decimal(m.get("op_stock", ""))
                if ops is not None:
                    obj.op_stock = ops

                opr = to_decimal(m.get("op_rate", ""))
                if opr is not None:
                    obj.op_rate = opr
                    
                inv_method = m.get("inv_method", "").upper()
                if inv_method in ("FIFO", "WAC"):
                    obj.inv_method = inv_method                
                
                inv_acc = m.get("inv_acc", "").lower()
                if inv_acc:
                    obj.inv_acc = inv_acc

                if barcode_obj is not None:
                    obj.main_barcode = barcode_obj

                obj.purchase_info       = True
                obj.sales_info      = True
                
                # ── Audit ────────────────────────────────────────────────────

                # Track created_by if available
                if request.user.is_authenticated:
                    if not exists:
                        obj.created_by = request.user
                    obj.updated_by = request.user

                if not exists:
                    obj.id = None  # ensure clean insert

                obj.save()

                if exists:
                    updated_count += 1
                else:
                    created_count += 1

            except Exception as exc:
                error_msgs.append(f"Row '{name}': {exc}")

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
                f"Import complete — {created_count} item(s) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        if created_units:
            preview_units = ", ".join(sorted(created_units)[:5])
            messages.info(
                request,
                f"New units were added to Unit master during import: {preview_units}"
            )
        if created_brands:
            preview_brands = ", ".join(sorted(created_brands)[:5])
            messages.info(
                request,
                f"New brands were added to Brand master during import: {preview_brands}"
            )
        if created_types:
            preview_types = ", ".join(sorted(created_types)[:5])
            messages.info(
                request,
                f"New types were added to Type master during import: {preview_types}"
            )
        if created_categories:
            preview_categories = ", ".join(sorted(created_categories)[:5])
            messages.info(
                request,
                f"New categories were added to Category master during import: {preview_categories}"
            )
        if missing_vendors:
            preview_vendors = ", ".join(sorted(missing_vendors)[:5])
            messages.info(
                request,
                f"Preferred vendors were not found and were skipped: {preview_vendors}"
            )

        return redirect("items", company_code=company_code)

    return render(request, "import_step3.html", {
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

def import_items_sample(request, company_code):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_items.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in IMPORT_FIELDS])
    writer.writerow([
        # basic
        "Laptop Stand", "goods", "pcs", "Acme","electronics", "stand", "", "","",
        # sales
        "999.00", "Sales", "Ergonomic laptop stand", "false",
        # purchase
        "750.00", "Purchases", "Laptop stand for resale", "false", "Tech Supplier Ltd",
        # tax
        "taxable", "IGST 18%", "GST 18%",
        # inventory
        "false", "50", "600.00", "FIFO", "inv_asset", "10",
    ])
    writer.writerow([
        # basic
        "Web Design Service", "service", "hrs", "Creative Co","", "", "", "","",
        # sales
        "5000.00", "Sales", "Website design and development", "false",
        # purchase
        "3000.00", "Purchases", "Outsourced design work", "false", "",
        # tax
        "taxable", "", "",
        # inventory
        "false", "", "", "FIFO", "", "",
    ])
    return response
