# -*- coding: utf-8 -*-
"""
In-memory Word document (.docx) builder for the Weekly BSC Management Report.
Performs 100% in-memory compilation without creating database records in Odoo.
"""

import io
from typing import Optional
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls


def set_cell_properties(cell, width_dxa=None, fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100):
    tcPr = cell._tc.get_or_add_tcPr()

    if width_dxa is not None:
        tcW = tcPr.find(qn('w:tcW'))
        if tcW is None:
            tcW = OxmlElement('w:tcW')
            tcPr.append(tcW)
        tcW.set(qn('w:w'), str(width_dxa))
        tcW.set(qn('w:type'), 'dxa')

    tcBorders = tcPr.find(qn('w:tcBorders'))
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)
    else:
        tcBorders.clear()

    for border_name in ['top', 'left', 'bottom', 'right']:
        node = OxmlElement(f'w:{border_name}')
        node.set(qn('w:val'), 'single')
        node.set(qn('w:sz'), '4')
        node.set(qn('w:space'), '0')
        node.set(qn('w:color'), 'auto')
        tcBorders.append(node)

    tcPr_shd = tcPr.find(qn('w:shd'))
    if fill_hex:
        if tcPr_shd is None:
            tcPr_shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill_hex}"/>')
            tcPr.append(tcPr_shd)
        else:
            tcPr_shd.set(qn('w:val'), 'clear')
            tcPr_shd.set(qn('w:color'), 'auto')
            tcPr_shd.set(qn('w:fill'), fill_hex)
    else:
        if tcPr_shd is not None:
            tcPr.remove(tcPr_shd)

    tcMar = tcPr.find(qn('w:tcMar'))
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar')
        tcPr.append(tcMar)
    else:
        tcMar.clear()

    for m_name, m_val in [('top', top_mar), ('bottom', bottom_mar), ('left', left_mar), ('right', right_mar)]:
        node = OxmlElement(f'w:{m_name}')
        node.set(qn('w:w'), str(m_val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)

    vAlign = tcPr.find(qn('w:vAlign'))
    if vAlign is None:
        vAlign = OxmlElement('w:vAlign')
        tcPr.append(vAlign)
    vAlign.set(qn('w:val'), 'center')


def format_cell_text(cell, text, bold=False, italic=False, font_name="Calibri Light", font_size=9.5, color_rgb=RGBColor(0, 0, 0), align=WD_ALIGN_PARAGRAPH.LEFT):
    p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    p.text = ""
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(str(text))
    run.bold = bold
    run.italic = italic
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.color.rgb = color_rgb
    return p


def format_currency(val):
    if val is None or val == "":
        return "฿ 0.00"
    try:
        f_val = float(val)
        if f_val < 0:
            return f"-฿ {abs(f_val):,.2f}"
        return f"฿ {f_val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def format_pct(val):
    if val is None or val == "":
        return "0.0%"
    try:
        f_val = float(val)
        return f"{f_val:.1f}%"
    except (ValueError, TypeError):
        return str(val)


def build_bsc_document_bytes(data: dict, narrative: Optional[dict] = None, template_bytes: Optional[bytes] = None) -> bytes:
    """Builds the complete Word document in memory from data and template bytes."""
    narrative = narrative or {}
    if template_bytes:
        doc = docx.Document(io.BytesIO(template_bytes))
    else:
        doc = docx.Document()

    week_info = data.get("week_info", {})
    week_num = week_info.get("week_number", "—")
    period_label = week_info.get("period_label", "—")

    # 1. Update Title and Subtitle Paragraphs
    for p in doc.paragraphs:
        if "Weekly Management Report — Week" in p.text:
            p.text = f"Weekly Management Report — Week {week_num}"
            if p.runs:
                p.runs[0].bold = True
                p.runs[0].font.name = "Calibri Light"
                p.runs[0].font.size = Pt(16)
                p.runs[0].font.color.rgb = RGBColor(0, 0, 0)
        elif "Reporting period:" in p.text:
            p.text = f"Reporting period: {period_label} | Infinity IT Group"
            if p.runs:
                p.runs[0].font.name = "Calibri Light"
                p.runs[0].font.size = Pt(10)
                p.runs[0].font.color.rgb = RGBColor(85, 85, 85)

    # 2. Executive Summary - Insert strictly between EXECUTIVE SUMMARY heading and Table 0
    exec_summary_text = narrative.get("executive_summary", "")
    if exec_summary_text and len(doc.paragraphs) > 3:
        lines = [line.strip() for line in exec_summary_text.strip().split("\n") if line.strip()]
        if lines:
            p_curr = doc.paragraphs[3]
            p_curr.text = lines[0]
            if p_curr.runs:
                p_curr.runs[0].font.name = "Calibri Light"
                p_curr.runs[0].font.size = Pt(10)
                p_curr.runs[0].font.color.rgb = RGBColor(30, 41, 59)
            p_curr.paragraph_format.space_before = Pt(2)
            p_curr.paragraph_format.space_after = Pt(3)
            p_curr.paragraph_format.line_spacing = 1.15

            for line in lines[1:]:
                new_p_elem = OxmlElement('w:p')
                p_curr._p.addnext(new_p_elem)
                new_p = docx.text.paragraph.Paragraph(new_p_elem, doc)
                new_p.text = line
                if new_p.runs:
                    new_p.runs[0].font.name = "Calibri Light"
                    new_p.runs[0].font.size = Pt(10)
                    new_p.runs[0].font.color.rgb = RGBColor(30, 41, 59)
                new_p.paragraph_format.space_before = Pt(2)
                new_p.paragraph_format.space_after = Pt(3)
                new_p.paragraph_format.line_spacing = 1.15
                p_curr = new_p

    # 3. Helpdesk Table (Table index 3)
    if len(doc.tables) > 3:
        t_hd = doc.tables[3]
        hd_summary = data.get("p3_helpdesk", {}).get("summary", {})
        if len(t_hd.rows) > 1:
            row = t_hd.rows[1]
            format_cell_text(row.cells[0], hd_summary.get("new_this_week", 0), bold=True, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
            format_cell_text(row.cells[1], hd_summary.get("solved_this_week", 0), bold=True, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
            format_cell_text(row.cells[2], hd_summary.get("currently_open", 0), bold=True, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
            avg_res = hd_summary.get("avg_resolve_hours", 0.0)
            format_cell_text(row.cells[3], f"{avg_res:.1f} hrs", bold=True, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    # 4. Leads by Phase Table (Table index 5)
    if len(doc.tables) > 5:
        t_phase = doc.tables[5]
        phases_data = {r["phase"]: r for r in data.get("p2_pipeline", {}).get("leads_by_phase", [])}
        for r_idx in range(1, len(t_phase.rows)):
            row = t_phase.rows[r_idx]
            phase_name = row.cells[0].text.strip()
            p_data = phases_data.get(phase_name)
            if p_data:
                is_total = (phase_name == "Total")
                format_cell_text(row.cells[1], p_data.get("leads_count", 0), bold=is_total, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
                format_cell_text(row.cells[2], format_currency(p_data.get("value", 0.0)), bold=is_total, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

    # 5. New Leads Entered This Week Table (Table index 6)
    if len(doc.tables) > 6:
        t_new_leads = doc.tables[6]
        new_leads = data.get("p2_pipeline", {}).get("new_leads_this_week", [])
        col_widths = [3800, 2400, 1400, 1600, 1000]

        target_rows = max(len(new_leads), 1) + 1
        while len(t_new_leads.rows) > target_rows:
            t_new_leads._tbl.remove(t_new_leads.rows[-1]._tr)
        while len(t_new_leads.rows) < target_rows:
            t_new_leads.add_row()

        if not new_leads:
            row = t_new_leads.rows[1]
            for c_idx in range(5):
                set_cell_properties(row.cells[c_idx], width_dxa=col_widths[c_idx])
            format_cell_text(row.cells[0], "None this week", italic=True, font_name="Calibri Light", font_size=9.5)
            for c_idx in range(1, 5):
                format_cell_text(row.cells[c_idx], "—", font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER)
        else:
            for idx, nl in enumerate(new_leads):
                row = t_new_leads.rows[idx + 1]
                for c_idx in range(5):
                    set_cell_properties(row.cells[c_idx], width_dxa=col_widths[c_idx])
                format_cell_text(row.cells[0], nl.get("opportunity", ""), font_name="Calibri Light", font_size=9.5)
                format_cell_text(row.cells[1], nl.get("salesperson", ""), font_name="Calibri Light", font_size=9.5)
                format_cell_text(row.cells[2], nl.get("stage", ""), font_name="Calibri Light", font_size=9.5)
                format_cell_text(row.cells[3], format_currency(nl.get("value", 0.0)), font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.RIGHT)
                format_cell_text(row.cells[4], nl.get("created", ""), font_name="Calibri Light", font_size=9, color_rgb=RGBColor(85, 85, 85), align=WD_ALIGN_PARAGRAPH.CENTER)

    # 6. Open Pipeline by Salesperson Table (Table index 7)
    if len(doc.tables) > 7:
        t_sp = doc.tables[7]
        sp_pipeline = data.get("p2_pipeline", {}).get("open_pipeline_by_salesperson", [])
        col_widths = [4200, 2200, 3800]

        while len(t_sp.rows) > 1:
            t_sp._tbl.remove(t_sp.rows[-1]._tr)

        total_leads = sum(s.get("open_leads", 0) for s in sp_pipeline)
        total_value = sum(s.get("open_value", 0.0) for s in sp_pipeline)

        for sp in sp_pipeline:
            row = t_sp.add_row()
            for c_idx in range(3):
                set_cell_properties(row.cells[c_idx], width_dxa=col_widths[c_idx])
            format_cell_text(row.cells[0], sp.get("salesperson", ""), font_name="Calibri Light", font_size=9.5)
            format_cell_text(row.cells[1], sp.get("open_leads", 0), font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER)
            format_cell_text(row.cells[2], format_currency(sp.get("open_value", 0.0)), font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.RIGHT)

        row_tot = t_sp.add_row()
        for c_idx in range(3):
            set_cell_properties(row_tot.cells[c_idx], width_dxa=col_widths[c_idx])
        format_cell_text(row_tot.cells[0], "Total", bold=True, font_name="Calibri Light", font_size=9.5)
        format_cell_text(row_tot.cells[1], total_leads, bold=True, font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER)
        format_cell_text(row_tot.cells[2], format_currency(total_value), bold=True, font_name="Calibri Light", font_size=9.5, align=WD_ALIGN_PARAGRAPH.RIGHT)

    # Helper: Create full-width 1x1 pillar banner table
    def create_banner_table(text):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        tblPr = tbl._tbl.tblPr
        tblW = tblPr.find(qn('w:tblW'))
        if tblW is None:
            tblW = OxmlElement('w:tblW')
            tblPr.append(tblW)
        tblW.set(qn('w:w'), '10200')
        tblW.set(qn('w:type'), 'dxa')
        cell = tbl.rows[0].cells[0]
        set_cell_properties(cell, width_dxa=10200, fill_hex="44546A", top_mar=80, bottom_mar=80, left_mar=120, right_mar=120)
        format_cell_text(cell, text, bold=True, font_name="Calibri Light", font_size=11, color_rgb=RGBColor(255, 255, 255), align=WD_ALIGN_PARAGRAPH.LEFT)
        return tbl

    # Helper: Create styled P&L table
    def create_pnl_table(rows_data, is_ytd=False):
        cols_count = 4 if is_ytd else 2
        col_widths = [4200, 2000, 2000, 2000] if is_ytd else [6200, 4000]
        headers = ["Line Item", "YTD Actual (THB)", "YTD Budget (THB)", "Variance (%)"] if is_ytd else ["Line Item", "Actual (THB)"]

        tbl = doc.add_table(rows=1 + len(rows_data), cols=cols_count)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False

        tblPr = tbl._tbl.tblPr
        tblW = tblPr.find(qn('w:tblW'))
        if tblW is None:
            tblW = OxmlElement('w:tblW')
            tblPr.append(tblW)
        tblW.set(qn('w:w'), '10200')
        tblW.set(qn('w:type'), 'dxa')

        hdr = tbl.rows[0]
        for c_idx, h_text in enumerate(headers):
            cell = hdr.cells[c_idx]
            set_cell_properties(cell, width_dxa=col_widths[c_idx], fill_hex="44546A", top_mar=60, bottom_mar=60, left_mar=100, right_mar=100)
            align = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.RIGHT
            format_cell_text(cell, h_text, bold=True, font_name="Calibri Light", font_size=11, color_rgb=RGBColor(255, 255, 255), align=align)

        for r_idx, r_data in enumerate(rows_data):
            row = tbl.rows[r_idx + 1]
            label = r_data.get("label", "")
            is_pct = r_data.get("is_percentage", False)
            is_summary = any(k in label.lower() for k in ["total", "gross profit", "ebitda", "ebit", "ebt", "net income"])

            c0 = row.cells[0]
            set_cell_properties(c0, width_dxa=col_widths[0], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
            format_cell_text(c0, label, bold=is_summary, font_name="Calibri Light", font_size=10)

            c1 = row.cells[1]
            set_cell_properties(c1, width_dxa=col_widths[1], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
            act_str = format_pct(r_data.get("actual")) if is_pct else format_currency(r_data.get("actual"))
            format_cell_text(c1, act_str, bold=is_summary, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

            if is_ytd:
                c2 = row.cells[2]
                set_cell_properties(c2, width_dxa=col_widths[2], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
                bud_str = format_pct(r_data.get("budget")) if is_pct else format_currency(r_data.get("budget"))
                format_cell_text(c2, bud_str, bold=is_summary, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

                c3 = row.cells[3]
                set_cell_properties(c3, width_dxa=col_widths[3], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
                var_str = r_data.get("variance_pct_str", "—")
                var_color = RGBColor(0, 0, 0)
                if var_str.startswith("+"):
                    var_color = RGBColor(22, 101, 52)
                elif var_str.startswith("-"):
                    var_color = RGBColor(185, 28, 28)
                format_cell_text(c3, var_str, bold=is_summary, font_name="Calibri Light", font_size=10, color_rgb=var_color, align=WD_ALIGN_PARAGRAPH.RIGHT)

        return tbl

    # 7. Financial Stewardship Banner (P1)
    has_p1 = any("P1 · FINANCIAL" in cell.text for t in doc.tables for r in t.rows for cell in r.cells)
    if not has_p1:
        for p in doc.paragraphs:
            if "Income statement, Week" in p.text:
                banner_tbl = create_banner_table("P1 · FINANCIAL — STEWARDSHIP")
                p._p.addprevious(banner_tbl._tbl)
                break

    # 8. Weekly P&L Table
    for p in doc.paragraphs:
        if "Income statement, Week" in p.text:
            p.text = f"Income statement, Week {week_num}"
            if p.runs:
                p.runs[0].bold = True
                p.runs[0].font.name = "Calibri Light"
                p.runs[0].font.size = Pt(11)
            tbl_pnl = create_pnl_table(data.get("p1_financial", {}).get("weekly_pnl", []))
            p._p.addnext(tbl_pnl._tbl)
            break

    # 9. YTD P&L Table
    for p in doc.paragraphs:
        if "Profit & Loss, YTD + Budget + Variance" in p.text:
            if p.runs:
                p.runs[0].bold = True
                p.runs[0].font.name = "Calibri Light"
                p.runs[0].font.size = Pt(11)
            tbl_ytd = create_pnl_table(data.get("p1_financial", {}).get("ytd_pnl_budget", []), is_ytd=True)
            p._p.addnext(tbl_ytd._tbl)
            break

    # 10. Balance Sheet Table
    bs_data = data.get("p1_financial", {}).get("balance_sheet", [])
    bs_dict = {r.get("metric"): r.get("actual") for r in bs_data}
    col_widths = [6200, 4000]

    # Find existing Balance Sheet table in template (2 cols, header starts with 'Metric')
    tbl_bs = None
    for t in doc.tables:
        if len(t.rows) > 0 and len(t.columns) == 2:
            if t.rows[0].cells[0].text.strip() == "Metric":
                tbl_bs = t
                break

    if tbl_bs is not None:
        # Style existing template header
        set_cell_properties(tbl_bs.rows[0].cells[0], width_dxa=col_widths[0], fill_hex="44546A", top_mar=60, bottom_mar=60, left_mar=100, right_mar=100)
        format_cell_text(tbl_bs.rows[0].cells[0], "Metric", bold=True, font_name="Calibri Light", font_size=11, color_rgb=RGBColor(255, 255, 255), align=WD_ALIGN_PARAGRAPH.LEFT)
        set_cell_properties(tbl_bs.rows[0].cells[1], width_dxa=col_widths[1], fill_hex="44546A", top_mar=60, bottom_mar=60, left_mar=100, right_mar=100)
        format_cell_text(tbl_bs.rows[0].cells[1], "Actual (THB)", bold=True, font_name="Calibri Light", font_size=11, color_rgb=RGBColor(255, 255, 255), align=WD_ALIGN_PARAGRAPH.RIGHT)

        # Populate rows
        for r_idx in range(1, len(tbl_bs.rows)):
            row = tbl_bs.rows[r_idx]
            metric_name = row.cells[0].text.strip()
            val = bs_dict.get(metric_name)
            is_summary = any(k in metric_name.lower() for k in ["total", "working capital"])

            set_cell_properties(row.cells[0], width_dxa=col_widths[0], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
            format_cell_text(row.cells[0], metric_name, bold=is_summary, font_name="Calibri Light", font_size=10)

            set_cell_properties(row.cells[1], width_dxa=col_widths[1], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
            format_cell_text(row.cells[1], format_currency(val) if val is not None else "—", bold=is_summary, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
    else:
        # Fallback if no template table found: create new table under 'Balance Sheet' paragraph
        for p in doc.paragraphs:
            if "Balance Sheet" in p.text and p.text.strip() == "Balance Sheet":
                if p.runs:
                    p.runs[0].bold = True
                    p.runs[0].font.name = "Calibri Light"
                    p.runs[0].font.size = Pt(11)

                tbl_new = doc.add_table(rows=1 + len(bs_data), cols=2)
                tbl_new.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl_new.autofit = False

                tblPr = tbl_new._tbl.tblPr
                tblW = tblPr.find(qn('w:tblW'))
                if tblW is None:
                    tblW = OxmlElement('w:tblW')
                    tblPr.append(tblW)
                tblW.set(qn('w:w'), '10200')
                tblW.set(qn('w:type'), 'dxa')

                hdr = tbl_new.rows[0]
                for c_idx, h_text in enumerate(["Metric", "Actual (THB)"]):
                    cell = hdr.cells[c_idx]
                    set_cell_properties(cell, width_dxa=col_widths[c_idx], fill_hex="44546A", top_mar=60, bottom_mar=60, left_mar=100, right_mar=100)
                    align = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.RIGHT
                    format_cell_text(cell, h_text, bold=True, font_name="Calibri Light", font_size=11, color_rgb=RGBColor(255, 255, 255), align=align)

                for r_idx, r_data in enumerate(bs_data):
                    row = tbl_new.rows[r_idx + 1]
                    metric_name = r_data.get("metric", "")
                    is_summary = any(k in metric_name.lower() for k in ["total", "working capital"])

                    c0 = row.cells[0]
                    set_cell_properties(c0, width_dxa=col_widths[0], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
                    format_cell_text(c0, metric_name, bold=is_summary, font_name="Calibri Light", font_size=10)

                    c1 = row.cells[1]
                    set_cell_properties(c1, width_dxa=col_widths[1], fill_hex=None, top_mar=50, bottom_mar=50, left_mar=100, right_mar=100)
                    format_cell_text(c1, format_currency(r_data.get("actual")), bold=is_summary, font_name="Calibri Light", font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

                p._p.addnext(tbl_new._tbl)
                break

    out_io = io.BytesIO()
    doc.save(out_io)
    return out_io.getvalue()

