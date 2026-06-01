import re


def _build_logo_src(logo_value):
    if not logo_value:
        return ""

    if logo_value.startswith("data:image"):
        return logo_value

    mime_type = "image/png"
    if logo_value.startswith("/9j/"):
        mime_type = "image/jpeg"
    elif logo_value.startswith("iVBORw0KGgo"):
        mime_type = "image/png"
    elif logo_value.startswith("R0lGOD"):
        mime_type = "image/gif"
    elif logo_value.startswith("UklGR"):
        mime_type = "image/webp"

    return f"data:{mime_type};base64,{logo_value}"


def replace_placeholders(body, context):
    company_name = str(context.get("company", "") or "")
    logo_value = str(context.get("logo", "") or "")
    logo_src = _build_logo_src(logo_value)
    logo_html = (
        f'<img src="{logo_src}" alt="{company_name or "Company"} Logo" '
        'style="display:block;max-width:40px;max-height:40px;width:auto;height:auto;margin:0 auto;" width="40" height="40">'
        if logo_src
        else '<span style="color:#ffffff;">&#9889;</span>'
    )

    body = body.replace("[[logo]]", logo_html)

    for key, value in context.items():
        if key == "logo":
            continue
        body = body.replace(f"[[{key}]]", str(value))

    body = body.replace("[[logo]]", '<span style="color:#ffffff;">[[logo]]</span>')
    body = body.replace("[[company]]", '<span style="color:#ffffff;">[[company]]</span>')

    if company_name:
        body = body.replace(">Lyra ERP<", f">{company_name}<")
        body = body.replace("Lyra ERP. All rights reserved.", f"{company_name}. All rights reserved.")

    if logo_src:
        body = re.sub(
            r'<td[^>]*width:36px;height:36px[^>]*>.*?</td>',
            (
                '<td style="width:36px;height:36px;text-align:center;vertical-align:middle;">'
                f'{logo_html}'
                '</td>'
            ),
            body,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    else:
        body = re.sub(
            r'(<td[^>]*width:36px;height:36px[^>]*>)(.*?)(</td>)',
            rf"\1{logo_html}\3",
            body,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )

    return body
