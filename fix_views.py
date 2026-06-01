import sys

file_path = 'd:/LyraSixShare/Lyraerp/Lyraerp/Lyraerp/sales/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    # ITEMS TABLE - Professional styling with conditional VAT/CGST-SGST
    currency = "₹" if font_registered else "Rs."
    company_is_india = context.get('company_is_india', True)
    
    # Conditional table headers based on country
    if company_is_india:
        items_data = [
            [Paragraph("<b>#</b>", label_style), 
             Paragraph("<b>Item & Description</b>", label_style),
             Paragraph("<b>HSN/SAC</b>", label_style),
             Paragraph("<b>Qty</b>", label_style),
             Paragraph("<b>Rate</b>", label_style),
             Paragraph("<b>CGST</b>", label_style),
             Paragraph("<b>SGST</b>", label_style)]
        ]
    else:
        items_data = [
            [Paragraph("<b>#</b>", label_style), 
             Paragraph("<b>Item & Description</b>", label_style),
             Paragraph("<b>HSN/SAC</b>", label_style),
             Paragraph("<b>Qty</b>", label_style),
             Paragraph("<b>Rate</b>", label_style),
             Paragraph("<b>Tax Rate</b>", label_style),
             Paragraph("<b>Tax Amount</b>", label_style)]
        ]
    
    for idx, item in enumerate(context.get('items_info', []), 1):
        tax_rate = Decimal(str(item.get('tax_rate', 0)))
        tax_amount = Decimal(str(item.get('tax_amount', 0)))
        
        if company_is_india:
            # Split tax equally for India (CGST/SGST)
            cgst_rate = tax_rate / 2
            sgst_rate = tax_rate / 2
            cgst_amount = tax_amount / 2
            sgst_amount = tax_amount / 2
            items_data.append([
            Paragraph(str(idx), value_style),
            Paragraph(f"{item.get('product_name', '')}<br/><font size=6><i>{item.get('description', '')}</i></font>", value_style),
            Paragraph(item.get('hsn', '-'), value_style),
            Paragraph(str(item.get('quantity', '')), ParagraphStyle('Right', parent=styles['Normal'], fontSize=8, fontName=font_name, alignment=TA_RIGHT)),
            Paragraph(f"{currency}\\u00A0{item.get('price', 0):.2f}", amount_style),
            Paragraph(f"{cgst_rate:.2f}%<br/>{currency}\\u00A0{float(cgst_amount):.2f}", amount_style),
            Paragraph(f"{sgst_rate:.2f}%<br/>{currency}\\u00A0{float(sgst_amount):.2f}", amount_style),
        ])
        else:
            items_data.append([
                Paragraph(str(idx), value_style),
                Paragraph(f"{item.get('product_name', '')}<br/><font size=6><i>{item.get('description', '')}</i></font>", value_style),
                Paragraph(item.get('hsn', '-'), value_style),
                Paragraph(str(item.get('quantity', '')), ParagraphStyle('Right', parent=styles['Normal'], fontSize=8, fontName=font_name, alignment=TA_RIGHT)),
                Paragraph(f"{currency}\\u00A0{item.get('price', 0):.2f}", amount_style),
                Paragraph(f"{tax_rate:.2f}%", amount_style),
                Paragraph(f"{currency}\\u00A0{float(tax_amount):.2f}", amount_style),
            ])"""

replacement = """    # ITEMS TABLE - Professional styling with conditional VAT/CGST-SGST
    currency = context.get('document_currency_symbol') or ("₹" if font_registered else "Rs.")
    base_currency = context.get('company_base_currency_symbol') or ("₹" if font_registered else "Rs.")
    company_is_india = context.get('company_is_india', True)
    
    # Conditional table headers based on country
    if company_is_india:
        items_data = [
            [Paragraph("<b>#</b>", label_style), 
             Paragraph("<b>Item & Description</b>", label_style),
             Paragraph("<b>HSN/SAC</b>", label_style),
             Paragraph("<b>Qty</b>", label_style),
             Paragraph("<b>Rate</b>", label_style),
             Paragraph("<b>CGST</b>", label_style),
             Paragraph("<b>SGST</b>", label_style)]
        ]
    else:
        items_data = [
            [Paragraph("<b>#</b>", label_style), 
             Paragraph("<b>Item & Description</b>", label_style),
             Paragraph("<b>HSN/SAC</b>", label_style),
             Paragraph("<b>Qty</b>", label_style),
             Paragraph("<b>Rate</b>", label_style),
             Paragraph("<b>Tax Rate</b>", label_style),
             Paragraph("<b>Tax Amount</b>", label_style)]
        ]
    
    for idx, item in enumerate(context.get('items_info', []), 1):
        tax_rate = Decimal(str(item.get('tax_rate', 0)))
        tax_amount = Decimal(str(item.get('tax_amount', 0)))
        
        base_price_str = f"<br/><font size=6 color='#7f8c8d'>({base_currency}\\u00A0{float(item.get('price_base', 0)):.2f})</font>" if item.get('price_base') else ""
        tax_base_str = f"<br/><font size=6 color='#7f8c8d'>({base_currency}\\u00A0{float(item.get('tax_amount_base', 0)):.2f})</font>" if item.get('tax_amount_base') else ""

        if company_is_india:
            # Split tax equally for India (CGST/SGST)
            cgst_rate = tax_rate / 2
            sgst_rate = tax_rate / 2
            cgst_amount = tax_amount / 2
            sgst_amount = tax_amount / 2

            cgst_base_str = f"<br/><font size=6 color='#7f8c8d'>({base_currency}\\u00A0{float(item.get('cgst_amount_base', 0)):.2f})</font>" if item.get('cgst_amount_base') else ""
            sgst_base_str = f"<br/><font size=6 color='#7f8c8d'>({base_currency}\\u00A0{float(item.get('sgst_amount_base', 0)):.2f})</font>" if item.get('sgst_amount_base') else ""

            items_data.append([
                Paragraph(str(idx), value_style),
                Paragraph(f"{item.get('product_name', '')}<br/><font size=6><i>{item.get('description', '')}</i></font>", value_style),
                Paragraph(item.get('hsn', '-'), value_style),
                Paragraph(str(item.get('quantity', '')), ParagraphStyle('Right', parent=styles['Normal'], fontSize=8, fontName=font_name, alignment=TA_RIGHT)),
                Paragraph(f"{currency}\\u00A0{item.get('price', 0):.2f}{base_price_str}", amount_style),
                Paragraph(f"{cgst_rate:.2f}%<br/>{currency}\\u00A0{float(cgst_amount):.2f}{cgst_base_str}", amount_style),
                Paragraph(f"{sgst_rate:.2f}%<br/>{currency}\\u00A0{float(sgst_amount):.2f}{sgst_base_str}", amount_style),
            ])
        else:
            items_data.append([
                Paragraph(str(idx), value_style),
                Paragraph(f"{item.get('product_name', '')}<br/><font size=6><i>{item.get('description', '')}</i></font>", value_style),
                Paragraph(item.get('hsn', '-'), value_style),
                Paragraph(str(item.get('quantity', '')), ParagraphStyle('Right', parent=styles['Normal'], fontSize=8, fontName=font_name, alignment=TA_RIGHT)),
                Paragraph(f"{currency}\\u00A0{item.get('price', 0):.2f}{base_price_str}", amount_style),
                Paragraph(f"{tax_rate:.2f}%", amount_style),
                Paragraph(f"{currency}\\u00A0{float(tax_amount):.2f}{tax_base_str}", amount_style),
            ])"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('Error: Target not found!')
