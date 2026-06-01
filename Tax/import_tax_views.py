"""
Tax Import Wizards - import_tax_views.py
Handles import for Tax and Tax Group with CSV/XLS(X) support.
"""

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from Lyraerp.utils.redirect_utils import redirect_with_company, get_company_code
from .models import Tax, TaxGroup

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


TAX_IMPORT_FIELDS = [
    ("taxname", "Tax Name", True, "basic", "taxname"),
    ("taxtype", "Tax Type", True, "basic", "taxtype"),
    ("rate", "Rate", True, "basic", "rate"),
]

TAXGROUP_IMPORT_FIELDS = [
    ("group_name", "Group Name", True, "basic", "group_name"),
    ("taxes", "Taxes", True, "basic", None),  # Special handling
]

SECTION_LABELS = {
    "basic": "Basic Details",
}

SECTIONS_ORDER = ["basic"]


def _get_fields_by_section(import_fields):
    result = {}
    for key, label, required, section, _ in import_fields:
        result.setdefault(section, []).append((key, label, required))
    return result


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


def _auto_map(headers, import_fields):
    mapping = {}
    for h in headers:
        h_norm = h.strip().lower().replace(" ", "_").replace("-", "_")
        for key, label, *_ in import_fields:
            label_norm = label.lower().replace(" ", "_")
            if h_norm == key or h_norm == label_norm or h_norm.startswith(key):
                mapping[h] = key
                break
    return mapping


def _validate_tax_rows(rows, mapping):
    allowed_types = {
        choice[0].lower(): choice[0]
        for choice in Tax.TAX_TYPE_CHOICES
        if choice[0]
    }
    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: row.get(csv_h, "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []

        name = mapped.get("taxname", "").strip()
        ttype_raw = mapped.get("taxtype", "").strip()
        rate_raw = mapped.get("rate", "").strip()

        if not name:
            errors.append("Tax Name is required")

        if not ttype_raw:
            errors.append("Tax Type is required")
            ttype = ""
        else:
            ttype = allowed_types.get(ttype_raw.lower())
            if not ttype:
                errors.append("Tax Type must be one of: CGST, SGST, IGST, UTGST, Cess")
                ttype = ""

        if not rate_raw:
            errors.append("Rate is required")
            rate_val = None
        else:
            try:
                rate_val = Decimal(rate_raw)
            except (InvalidOperation, ValueError):
                errors.append("Rate must be a number")
                rate_val = None

        if ttype:
            mapped["taxtype"] = ttype
        if rate_val is not None:
            mapped["rate"] = str(rate_val)

        entry = {
            "row": row,
            "mapped": mapped,
            "errors": errors,
            "name": name or "-"
        }
        (skipped if errors else ready).append(entry)
    return ready, skipped


def _split_tax_token(token, allowed_types):
    raw = token.strip()
    name = raw
    ttype = None
    rate = None

    if "(" in raw and raw.endswith(")"):
        name = raw[:raw.rfind("(")].strip()
        ttype = raw[raw.rfind("(") + 1:-1].strip()

    if "-" in raw:
        left, right = raw.split("-", 1)
        left = left.strip()
        right = right.strip()
        if left:
            name = left
        if right:
            ttype_norm = _normalize_tax_type(right, allowed_types)
            if ttype_norm:
                ttype = ttype_norm
            else:
                try:
                    rate = Decimal(right)
                except (InvalidOperation, ValueError):
                    rate = None

    if ttype:
        ttype = _normalize_tax_type(ttype, allowed_types)

    if rate is None:
        rate = _extract_rate_from_name(name)

    if not ttype:
        ttype = _infer_tax_type_from_name(name, allowed_types)

    return name, ttype, rate


def _normalize_tax_type(ttype_raw, allowed_types):
    if not ttype_raw:
        return None
    return allowed_types.get(ttype_raw.strip().lower())


def _infer_tax_type_from_name(name, allowed_types):
    if not name:
        return None
    first = name.strip().split()[0].lower()
    return allowed_types.get(first)


def _extract_rate_from_name(name):
    if not name:
        return None
    matches = re.findall(r"\d+(?:\.\d+)?", name)
    if not matches:
        return None
    try:
        return Decimal(matches[-1])
    except (InvalidOperation, ValueError):
        return None


def _validate_taxgroup_rows(rows, mapping):
    allowed_types = {
        choice[0].lower(): choice[0]
        for choice in Tax.TAX_TYPE_CHOICES
        if choice[0]
    }
    ready, skipped = [], []
    for row in rows:
        mapped = {fkey: row.get(csv_h, "").strip()
                  for csv_h, fkey in mapping.items()}
        errors = []

        name = mapped.get("group_name", "").strip()
        taxes_raw = mapped.get("taxes", "").strip()

        if not name:
            errors.append("Group Name is required")

        tax_ids = []
        tax_create_specs = []
        tax_reactivate_ids = []
        if taxes_raw:
            tokens = [t.strip() for t in taxes_raw.split(",") if t.strip()]
            if len(tokens) < 2:
                errors.append("At least two taxes are required for a group")
            for token in tokens:
                tname, ttype, rate_from_token = _split_tax_token(token, allowed_types)
                if not tname:
                    errors.append(f"Invalid tax token: {token}")
                    continue
                if ttype is None and token:
                    # If provided and invalid, flag it.
                    if "(" in token and token.strip().endswith(")"):
                        raw_type = token[token.rfind("(") + 1:-1].strip()
                        if raw_type:
                            errors.append("Tax Type must be one of: CGST, SGST, IGST, UTGST, Cess")
                            continue

                qs = Tax.objects.filter(taxname__iexact=tname)
                if ttype:
                    qs = qs.filter(taxtype__iexact=ttype)
                count = qs.count()
                if count == 0:
                    if not ttype:
                        errors.append(f"Tax Type missing for: {token}")
                        continue
                    rate_val = rate_from_token
                    if rate_val is None:
                        errors.append(f"Tax Rate missing in name for: {token}")
                        continue
                    key = (tname.lower(), ttype.lower())
                    if key not in {(s['taxname'].lower(), s['taxtype'].lower()) for s in tax_create_specs}:
                        tax_create_specs.append({
                            "taxname": tname,
                            "taxtype": ttype,
                            "rate": rate_val,
                        })
                elif count > 1 and not ttype:
                    errors.append(f"Multiple taxes match: {token} (add type)")
                else:
                    found = qs.first()
                    tax_ids.append(found.id)
                    if not found.status:
                        tax_reactivate_ids.append(found.id)
        else:
            errors.append("Taxes are needed")

        mapped["tax_ids"] = tax_ids
        mapped["tax_create_specs"] = tax_create_specs
        mapped["tax_reactivate_ids"] = tax_reactivate_ids

        entry = {
            "row": row,
            "mapped": mapped,
            "errors": errors,
            "name": name or "-"
        }
        (skipped if errors else ready).append(entry)
    return ready, skipped


def _session_set(request, prefix, data):
    for key, value in data.items():
        request.session[f"{prefix}_{key}"] = value


def _session_get(request, prefix, key, default=None):
    return request.session.get(f"{prefix}_{key}", default)


def _session_clear(request, prefix, keys):
    for key in keys:
        request.session.pop(f"{prefix}_{key}", None)


def import_tax_step1(request):
    company_code = get_company_code(request)
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "import_tax_step1.html", {"company_code": company_code})

        _session_set(request, "tax_imp", {
            "headers": headers,
            "rows": rows,
            "filename": uploaded.name,
            "duplicate": request.POST.get("duplicate_handling", "skip"),
            "row_count": len(rows),
        })

        return redirect_with_company(request, "import_tax_step2")

    return render(request, "import_tax_step1.html", {"company_code": company_code})


def import_tax_step2(request):
    company_code = get_company_code(request)
    headers = _session_get(request, "tax_imp", "headers")
    if not headers:
        return redirect_with_company(request, "import_tax_step1")

    filename = _session_get(request, "tax_imp", "filename", "")
    row_count = _session_get(request, "tax_imp", "row_count", 0)
    auto_map = _auto_map(headers, TAX_IMPORT_FIELDS)
    auto_map_inv = {v: k for k, v in auto_map.items()}

    if request.method == "POST":
        mapping = {}
        for key, _, required, *_ in TAX_IMPORT_FIELDS:
            csv_h = request.POST.get(f"map_{key}", "").strip()
            if csv_h:
                mapping[csv_h] = key
        missing_required = [
            label for key, label, required, *_ in TAX_IMPORT_FIELDS
            if required and key not in mapping.values()
        ]
        if missing_required:
            messages.error(request, "Required fields are missing: " + ", ".join(missing_required))
        else:
            _session_set(request, "tax_imp", {"mapping": mapping})
            return redirect_with_company(request, "import_tax_step3")

    fields_by_section = _get_fields_by_section(TAX_IMPORT_FIELDS)

    return render(request, "import_tax_step2.html", {
        "company_code": company_code,
        "filename": filename,
        "row_count": row_count,
        "headers": headers,
        "fields_by_section": fields_by_section,
        "sections_order": SECTIONS_ORDER,
        "section_labels": SECTION_LABELS,
        "auto_map_inv": auto_map_inv,
    })


def import_tax_step3(request):
    company_code = get_company_code(request)
    headers = _session_get(request, "tax_imp", "headers")
    rows = _session_get(request, "tax_imp", "rows")
    mapping = _session_get(request, "tax_imp", "mapping")
    duplicate = _session_get(request, "tax_imp", "duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect_with_company(request, "import_tax_step1")

    ready, skipped = _validate_tax_rows(rows, mapping)
    mapped_headers = set(mapping.keys())
    unmapped = [h for h in headers if h not in mapped_headers]

    if duplicate == "skip" and ready:
        from django.db.models import Q
        ready_keys = [
            (e["mapped"].get("taxname", "").strip(), e["mapped"].get("taxtype", "").strip())
            for e in ready
        ]
        ready_keys = [(n, t) for (n, t) in ready_keys if n and t]
        if ready_keys:
            q = Q()
            for name, ttype in ready_keys:
                q |= Q(taxname__iexact=name, taxtype__iexact=ttype)
            existing = set(
                Tax.objects.filter(q, status=True).values_list("taxname", "taxtype")
            )
            existing = {(n.lower(), t.lower()) for n, t in existing}
            if existing:
                next_ready = []
                for entry in ready:
                    name = entry["mapped"].get("taxname", "").strip()
                    ttype = entry["mapped"].get("taxtype", "").strip()
                    if name and ttype and (name.lower(), ttype.lower()) in existing:
                        entry = dict(entry)
                        entry["errors"] = entry.get("errors", []) + ["Duplicate tax exists (will be skipped)"]
                        skipped.append(entry)
                    else:
                        next_ready.append(entry)
                ready = next_ready

    if request.method == "POST" and request.POST.get("action") == "import":
        created_count = 0
        updated_count = 0
        skipped_dup = 0
        error_msgs = []

        for entry in ready:
            m = entry["mapped"]
            name = m.get("taxname", "").strip()
            ttype = m.get("taxtype", "").strip()
            rate_raw = m.get("rate", "").strip()
            if not (name and ttype and rate_raw):
                continue
            try:
                rate_val = Decimal(rate_raw)
            except (InvalidOperation, ValueError):
                error_msgs.append(f"Row '{name}': invalid rate")
                continue

            try:
                exists = Tax.objects.filter(taxname__iexact=name, taxtype__iexact=ttype).first()
                if exists and duplicate == "skip" and exists.status:
                    skipped_dup += 1
                    continue

                obj = exists or Tax()
                obj.taxname = name
                obj.taxtype = ttype
                obj.rate = rate_val
                obj.status = True

                if request.user.is_authenticated:
                    if not exists:
                        obj.crtd_by = request.user
                    obj.updt_by = request.user

                obj.save()

                if exists:
                    updated_count += 1
                else:
                    created_count += 1
            except Exception as exc:
                error_msgs.append(f"Row '{name}': {exc}")

        _session_clear(request, "tax_imp", [
            "headers", "rows", "filename", "mapping", "duplicate", "row_count"
        ])

        if error_msgs:
            messages.warning(request,
                f"Import finished with errors: {created_count} created, "
                f"{updated_count} updated, {skipped_dup} skipped, "
                f"{len(error_msgs)} failed.")
            for msg in error_msgs[:5]:
                messages.warning(request, msg)
        else:
            messages.success(request,
                f"Import complete - {created_count} tax(es) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        return redirect_with_company(request, "tax_list")

    return render(request, "import_tax_step3.html", {
        "company_code": company_code,
        "ready": ready,
        "skipped": skipped,
        "unmapped": unmapped,
        "total": len(rows),
        "duplicate": duplicate,
        "mapping": mapping,
    })


def import_tax_sample(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_taxes.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in TAX_IMPORT_FIELDS])
    writer.writerow(["CGST 5", "CGST", "5"])
    writer.writerow(["SGST 5", "SGST", "5"])
    return response


def import_taxgroup_step1(request):
    company_code = get_company_code(request)
    if request.method == "POST":
        uploaded = request.FILES.get("import_file")
        if not uploaded:
            messages.error(request, "Please select a file.")
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "tsv", "xls", "xlsx"):
            messages.error(request, "Only CSV, TSV, XLS, or XLSX files are supported.")
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        if uploaded.size > 25 * 1024 * 1024:
            messages.error(request, "File exceeds 25 MB limit.")
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        try:
            headers, rows = _parse_file(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        if not headers:
            messages.error(request, "No headers found. Ensure row 1 contains column names.")
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        if not rows:
            messages.error(request, "File has headers but no data rows.")
            return render(request, "import_taxgroup_step1.html", {"company_code": company_code})

        _session_set(request, "taxgrp_imp", {
            "headers": headers,
            "rows": rows,
            "filename": uploaded.name,
            "duplicate": request.POST.get("duplicate_handling", "skip"),
            "row_count": len(rows),
        })

        return redirect_with_company(request, "import_taxgroup_step2")

    return render(request, "import_taxgroup_step1.html", {"company_code": company_code})


def import_taxgroup_step2(request):
    company_code = get_company_code(request)
    headers = _session_get(request, "taxgrp_imp", "headers")
    if not headers:
        return redirect_with_company(request, "import_taxgroup_step1")

    filename = _session_get(request, "taxgrp_imp", "filename", "")
    row_count = _session_get(request, "taxgrp_imp", "row_count", 0)
    auto_map = _auto_map(headers, TAXGROUP_IMPORT_FIELDS)
    auto_map_inv = {v: k for k, v in auto_map.items()}

    if request.method == "POST":
        mapping = {}
        for key, _, required, *_ in TAXGROUP_IMPORT_FIELDS:
            csv_h = request.POST.get(f"map_{key}", "").strip()
            if csv_h:
                mapping[csv_h] = key
        missing_required = [
            label for key, label, required, *_ in TAXGROUP_IMPORT_FIELDS
            if required and key not in mapping.values()
        ]
        if missing_required:
            messages.error(request, "Required fields are missing: " + ", ".join(missing_required))
        else:
            _session_set(request, "taxgrp_imp", {"mapping": mapping})
            return redirect_with_company(request, "import_taxgroup_step3")

    fields_by_section = _get_fields_by_section(TAXGROUP_IMPORT_FIELDS)

    return render(request, "import_taxgroup_step2.html", {
        "company_code": company_code,
        "filename": filename,
        "row_count": row_count,
        "headers": headers,
        "fields_by_section": fields_by_section,
        "sections_order": SECTIONS_ORDER,
        "section_labels": SECTION_LABELS,
        "auto_map_inv": auto_map_inv,
    })


def import_taxgroup_step3(request):
    company_code = get_company_code(request)
    headers = _session_get(request, "taxgrp_imp", "headers")
    rows = _session_get(request, "taxgrp_imp", "rows")
    mapping = _session_get(request, "taxgrp_imp", "mapping")
    duplicate = _session_get(request, "taxgrp_imp", "duplicate", "skip")

    if not (headers and rows is not None and mapping is not None):
        return redirect_with_company(request, "import_taxgroup_step1")

    ready, skipped = _validate_taxgroup_rows(rows, mapping)
    mapped_headers = set(mapping.keys())
    unmapped = [h for h in headers if h not in mapped_headers]

    if duplicate == "skip" and ready:
        from django.db.models.functions import Lower
        ready_names = [e["mapped"].get("group_name", "").strip() for e in ready]
        ready_names = [n for n in ready_names if n]
        if ready_names:
            existing = set(
                TaxGroup.objects.annotate(name_l=Lower("group_name"))
                .filter(name_l__in=[n.lower() for n in ready_names], status=True)
                .values_list("name_l", flat=True)
            )
            if existing:
                next_ready = []
                for entry in ready:
                    name = entry["mapped"].get("group_name", "").strip()
                    if name and name.lower() in existing:
                        entry = dict(entry)
                        entry["errors"] = entry.get("errors", []) + ["Duplicate tax group exists (will be skipped)"]
                        skipped.append(entry)
                    else:
                        next_ready.append(entry)
                ready = next_ready

    if request.method == "POST" and request.POST.get("action") == "import":
        created_count = 0
        updated_count = 0
        skipped_dup = 0
        error_msgs = []

        for entry in ready:
            m = entry["mapped"]
            name = m.get("group_name", "").strip()
            tax_ids = m.get("tax_ids", [])
            tax_create_specs = m.get("tax_create_specs", [])
            tax_reactivate_ids = m.get("tax_reactivate_ids", [])
            if not name:
                continue
            try:
                for spec in tax_create_specs:
                    tname = spec.get("taxname", "").strip()
                    ttype = spec.get("taxtype", "").strip()
                    rate_val = spec.get("rate")
                    if not (tname and ttype and rate_val is not None):
                        continue
                    existing_tax = Tax.objects.filter(
                        taxname__iexact=tname, taxtype__iexact=ttype
                    ).first()
                    if existing_tax:
                        if not existing_tax.status:
                            existing_tax.status = True
                            existing_tax.save(update_fields=["status"])
                        tax_ids.append(existing_tax.id)
                        continue
                    new_tax = Tax(taxname=tname, taxtype=ttype, rate=rate_val)
                    if request.user.is_authenticated:
                        new_tax.crtd_by = request.user
                        new_tax.updt_by = request.user
                    new_tax.save()
                    tax_ids.append(new_tax.id)

                # De-duplicate while preserving order
                seen_ids = set()
                tax_ids = [i for i in tax_ids if not (i in seen_ids or seen_ids.add(i))]

                if tax_reactivate_ids:
                    Tax.objects.filter(id__in=tax_reactivate_ids).update(status=True)

                exists = TaxGroup.objects.filter(group_name__iexact=name).first()
                if exists and duplicate == "skip" and exists.status:
                    skipped_dup += 1
                    continue

                obj = exists or TaxGroup()
                obj.group_name = name
                obj.status = True
                if request.user.is_authenticated:
                    if not exists:
                        obj.crtd_by = request.user
                    obj.updt_by = request.user
                obj.save()
                obj.taxes.set(tax_ids)

                if exists:
                    updated_count += 1
                else:
                    created_count += 1
            except Exception as exc:
                error_msgs.append(f"Row '{name}': {exc}")

        _session_clear(request, "taxgrp_imp", [
            "headers", "rows", "filename", "mapping", "duplicate", "row_count"
        ])

        if error_msgs:
            messages.warning(request,
                f"Import finished with errors: {created_count} created, "
                f"{updated_count} updated, {skipped_dup} skipped, "
                f"{len(error_msgs)} failed.")
            for msg in error_msgs[:5]:
                messages.warning(request, msg)
        else:
            messages.success(request,
                f"Import complete - {created_count} tax group(s) created, "
                f"{updated_count} updated, {skipped_dup} duplicate(s) skipped.")

        return redirect_with_company(request, "tax_list")

    return render(request, "import_taxgroup_step3.html", {
        "company_code": company_code,
        "ready": ready,
        "skipped": skipped,
        "unmapped": unmapped,
        "total": len(rows),
        "duplicate": duplicate,
        "mapping": mapping,
    })


def import_taxgroup_sample(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sample_taxgroups.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _, label, *_ in TAXGROUP_IMPORT_FIELDS])
    writer.writerow(["GST 5 Group", "CGST 5 - 5, SGST 5 - 5"])
    writer.writerow(["GST 18 Group", "CGST 9 - 9, SGST 9 - 9"])
    return response
