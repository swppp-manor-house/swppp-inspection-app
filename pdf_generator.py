"""
PDF Generator for SWPPP Inspection Report
Uses ReportLab (pure Python) — works on any Python version, no fonttools dependency.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image
)
from reportlab.platypus.flowables import Flowable

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SIG_PATH = os.path.join(_SCRIPT_DIR, 'static', 'signature.png')


class CheckBox(Flowable):
    """A small filled or empty checkbox square."""
    def __init__(self, checked=False, size=8):
        super().__init__()
        self.checked = checked
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        self.canv.setLineWidth(1)
        self.canv.rect(0, 0, self.size, self.size, stroke=1, fill=1 if self.checked else 0)


def _cb_text(checked: bool) -> str:
    """Return unicode checkbox character for use in Paragraphs."""
    return '&#9632;' if checked else '&#9633;'


def generate_swppp_pdf(form_data: dict, output_path: str):
    """Generate the SWPPP inspection report PDF from form data using ReportLab."""

    # ── Extract form data ──────────────────────────────────────────────────────
    project_location   = form_data.get("project_location", "")
    inspection_date    = form_data.get("inspection_date_display", "")
    inspector_name     = form_data.get("inspector_name", "")
    inspector_contact  = form_data.get("inspector_contact", "")
    construction_phase = form_data.get("construction_phase", "")
    schedule           = form_data.get("inspection_schedule", "every4")

    storm_event        = form_data.get("storm_event", False)
    storm_start_date   = form_data.get("storm_start_date", "")
    storm_start_time   = form_data.get("storm_start_time", "")
    storm_duration     = form_data.get("storm_duration_hrs", "")
    storm_precip       = form_data.get("storm_precipitation_in", "")

    weather_opts       = form_data.get("weather_options", {})
    temperature        = form_data.get("temperature", "")
    weather_other      = form_data.get("weather_other", "")

    site_items_data    = form_data.get("site_items", {})
    comments           = form_data.get("comments", "")

    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # ── Styles ─────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('normal', fontSize=9.5, leading=13, fontName='Helvetica')
    bold   = ParagraphStyle('bold',   fontSize=9.5, leading=13, fontName='Helvetica-Bold')
    small  = ParagraphStyle('small',  fontSize=8,   leading=11, fontName='Helvetica')
    italic = ParagraphStyle('italic', fontSize=9,   leading=12, fontName='Helvetica-Oblique')
    title1 = ParagraphStyle('title1', fontSize=14,  leading=18, fontName='Helvetica-Bold', alignment=TA_CENTER)
    title2 = ParagraphStyle('title2', fontSize=13,  leading=17, fontName='Helvetica-Bold', alignment=TA_CENTER)
    section_hdr = ParagraphStyle('section_hdr', fontSize=11, leading=14, fontName='Helvetica-Bold')
    cert_text = ParagraphStyle('cert_text', fontSize=9, leading=13, fontName='Helvetica-Oblique',
                               alignment=TA_JUSTIFY, leftIndent=8, rightIndent=8)
    footer_style = ParagraphStyle('footer', fontSize=7.5, leading=10, fontName='Helvetica-Oblique',
                                  alignment=TA_CENTER, textColor=colors.grey)

    def field_row(label, value, label_width=None):
        """Return a Table row with label and underlined value."""
        lw = label_width or 2.2*inch
        vw = 6.3*inch - lw
        label_p = Paragraph(f'<b>{label}</b>', normal)
        value_p = Paragraph(value or '', normal)
        t = Table([[label_p, value_p]], colWidths=[lw, vw])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        return t

    def cb_yn(value):
        """Return checked/unchecked Yes No string."""
        yes = _cb_text(value == 'yes')
        no  = _cb_text(value == 'no')
        return f'{yes} Yes &nbsp;&nbsp; {no} No'

    def wc(key):
        return _cb_text(bool(weather_opts.get(key, False)))

    # ── Build document ─────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.55*inch,  bottomMargin=0.55*inch,
    )

    story = []
    W = 6.3*inch  # usable width

    # ── PAGE 1 ─────────────────────────────────────────────────────────────────
    story.append(Paragraph('SWPPP Inspection Report', title1))
    story.append(HRFlowable(width=W, thickness=2, color=colors.black, spaceAfter=6))

    story.append(Paragraph('General Information', section_hdr))
    story.append(Spacer(1, 4))

    story.append(field_row('Project Location:', project_location))
    story.append(Spacer(1, 3))
    story.append(field_row('Date of Inspection:', inspection_date, 1.6*inch))
    story.append(Spacer(1, 3))
    story.append(field_row("Inspector's Name:", inspector_name, 1.5*inch))
    story.append(Spacer(1, 3))
    story.append(field_row("Inspector's Contact Information:", inspector_contact, 2.4*inch))
    story.append(Spacer(1, 3))
    story.append(field_row('Describe current phase of construction:', construction_phase, 2.9*inch))
    story.append(Spacer(1, 4))

    # Inspection schedule
    s4  = _cb_text(schedule == 'every4')
    s5  = _cb_text(schedule == 'every5')
    smo = _cb_text(schedule == 'monthly')
    story.append(Paragraph('<b>Inspection Schedule:</b>', normal))
    story.append(Spacer(1, 3))
    sched_data = [[
        Paragraph(f'{s4} Every 4 days', normal),
        Paragraph(f'{s5} Every 5 days &amp; 24 hours after rain event', normal),
        Paragraph(f'{smo} Monthly (w/ county inspector approval)', normal),
    ]]
    sched_t = Table(sched_data, colWidths=[1.6*inch, 2.8*inch, 1.9*inch])
    sched_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(sched_t)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey, spaceBefore=6, spaceAfter=6))

    # ── Weather section ────────────────────────────────────────────────────────
    story.append(Paragraph('Weather Information', section_hdr))
    story.append(Spacer(1, 4))

    storm_yes = _cb_text(bool(storm_event))
    storm_no  = _cb_text(not bool(storm_event))
    story.append(Paragraph(
        f'<b>Has there been a storm event since the last inspection?</b> &nbsp; {storm_yes} Yes &nbsp;&nbsp; {storm_no} No',
        normal))
    story.append(Spacer(1, 4))

    if storm_event:
        storm_data = [
            [Paragraph('<b>Storm Start Date &amp; Time:</b>', normal),
             Paragraph(f'{storm_start_date} {storm_start_time}', normal),
             Paragraph('<b>Storm Duration (hrs):</b>', normal),
             Paragraph(storm_duration or '', normal)],
            [Paragraph('<b>Approximate Amount of Precipitation (in):</b>', normal),
             Paragraph(storm_precip or '', normal), '', ''],
        ]
        storm_t = Table(storm_data, colWidths=[2.1*inch, 1.3*inch, 1.6*inch, 1.3*inch])
        storm_t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
            ('LINEBELOW', (3,0), (3,0), 0.5, colors.black),
            ('LINEBELOW', (1,1), (1,1), 0.5, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(storm_t)
        story.append(Spacer(1, 4))

    weather_keys = ['Clear', 'Cloudy', 'Rain', 'Fog', 'Sleet', 'Snowing', 'High Winds']
    weather_cells = [Paragraph('<b>Weather at time of inspection:</b>', normal)]
    for wk in weather_keys:
        weather_cells.append(Paragraph(f'{wc(wk)} {wk}', normal))
    weather_cells.append(Paragraph(f'<b>Temp:</b> {temperature}', normal))

    col_widths = [1.9*inch] + [0.7*inch]*7 + [0.7*inch]
    weather_t = Table([weather_cells], colWidths=col_widths)
    weather_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(weather_t)

    if weather_other:
        story.append(Spacer(1, 3))
        story.append(Paragraph(f'<b>Other:</b> {weather_other}', normal))

    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey, spaceBefore=6, spaceAfter=6))

    # ── Certification box ──────────────────────────────────────────────────────
    cert_inner = Paragraph(
        '&#8220;I certify under penalty of law that this document and all attachments were prepared under my '
        'direction or supervision in accordance with a system designed to assure that qualified personnel '
        'properly gathered and evaluated the information submitted. Based on my inquiry of the person or '
        'persons who manage the system, or those persons directly responsible for gathering the information, '
        'the information submitted is, to the best of my knowledge and belief, true, accurate, and complete. '
        'I am aware that there are significant penalties for submitting false information, including the '
        'possibility of fine and imprisonment for knowing violations.&#8221;',
        cert_text)

    cert_header = Paragraph('<b><i>Certification Statement</i></b>', 
                            ParagraphStyle('ch', fontSize=11, leading=14, fontName='Helvetica-BoldOblique',
                                           alignment=TA_CENTER))
    cert_t = Table(
        [[cert_header], [cert_inner]],
        colWidths=[W]
    )
    cert_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.lightgrey),
        ('LINEBELOW', (0,0), (0,0), 2, colors.black),
        ('TOPPADDING', (0,0), (0,0), 5),
        ('BOTTOMPADDING', (0,0), (0,0), 5),
        ('TOPPADDING', (0,1), (0,1), 8),
        ('BOTTOMPADDING', (0,1), (0,1), 10),
    ]))
    story.append(cert_t)
    story.append(Spacer(1, 10))

    # ── Signature row ──────────────────────────────────────────────────────────
    sig_col1 = []
    if os.path.exists(_SIG_PATH):
        try:
            sig_img = Image(_SIG_PATH, width=1.8*inch, height=0.55*inch)
            sig_col1.append(sig_img)
        except Exception:
            sig_col1.append(Spacer(1, 0.55*inch))
    else:
        sig_col1.append(Spacer(1, 0.55*inch))

    sig_data = [[
        sig_col1[0],
        Paragraph(f'<b>{inspector_name}</b>', normal),
        Paragraph(f'<b>{inspection_date}</b>', normal),
    ]]
    sig_t = Table(sig_data, colWidths=[2.4*inch, 2.4*inch, 1.5*inch])
    sig_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW', (0,0), (0,0), 0.5, colors.black),
        ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
        ('LINEBELOW', (2,0), (2,0), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sig_t)

    sig_labels = Table([[
        Paragraph('<i>Signature of Inspector</i>', small),
        Paragraph('<i>Printed Name and Title</i>', small),
        Paragraph('<i>Date</i>', small),
    ]], colWidths=[2.4*inch, 2.4*inch, 1.5*inch])
    sig_labels.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sig_labels)

    # ── PAGE 2 ─────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('Overall Site Issues', title2))
    story.append(HRFlowable(width=W, thickness=2, color=colors.black, spaceAfter=4))
    story.append(Paragraph(
        'Below are some general site issues that should be assessed during inspections.',
        ParagraphStyle('note', fontSize=8.5, leading=11, fontName='Helvetica')))
    story.append(Spacer(1, 6))

    site_items_def = [
        (1,  "Is permit and SWPPP contact info posted near the entrance of the project site?", True),
        (2,  "Is the SWPPP up to date, available on site, and properly maintained?", False),
        (3,  "Are all inactive disturbed areas or slopes stabilized? If so, with what?", True),
        (4,  "Natural resources (wetlands, trees, etc.) protected with perimeter controls (silt fence, etc.)?", True),
        (5,  "Are porta-johns placed away from water sources, free of leaks and properly contained?", True),
        (6,  "Are perimeter controls (silt fence, etc.) adequately installed? Being maintained?", True),
        (7,  "Are discharge points and receiving waters free of any sediment deposits?", True),
        (8,  "Are all storm drain inlets properly protected?", True),
        (9,  "All stockpiles/construction materials located in approved areas & protected from erosion?", True),
        (10, "Is construction entrance stopping sediment from being tracked onto paved roads?", True),
        (11, "Is all trash being collected and being properly disposed of in dumpsters?", True),
        (12, "Are washout facilities (paint, concrete, etc.) present, clearly marked, and maintained?", True),
        (13, "Are vehicle and equipment fueling, cleaning, and maintenance areas free of spills, leaks, or other harmful material?", True),
        (14, "Are potential contaminant materials stored inside or under cover?", True),
        (15, "Are dumpsters on site being covered at the end of each day and during rain events?", True),
        (16, "(Other)", True),
    ]

    item_style = ParagraphStyle('item', fontSize=8.5, leading=11, fontName='Helvetica')
    yn_style   = ParagraphStyle('yn',   fontSize=8.5, leading=11, fontName='Helvetica', alignment=TA_CENTER)
    na_style   = ParagraphStyle('na',   fontSize=8.5, leading=11, fontName='Helvetica', alignment=TA_CENTER,
                                textColor=colors.grey)

    # Header row
    header_style = ParagraphStyle('hdr', fontSize=8.5, leading=11, fontName='Helvetica-Bold', alignment=TA_CENTER)
    table_data = [[
        Paragraph('Site Activity', ParagraphStyle('hdr_l', fontSize=8.5, leading=11, fontName='Helvetica-Bold')),
        Paragraph('Implemented?', header_style),
        Paragraph('Maintenance?', header_style),
        Paragraph('Notes', header_style),
    ]]

    for i, (num, desc, has_maint) in enumerate(site_items_def):
        item = site_items_data.get(str(num), {})
        impl  = item.get('implemented', '')
        maint = item.get('maintenance', '')
        notes = item.get('notes', '')

        impl_p  = Paragraph(cb_yn(impl), yn_style)
        maint_p = Paragraph(cb_yn(maint), yn_style) if has_maint else Paragraph('N/A', na_style)
        notes_p = Paragraph(notes or '', ParagraphStyle('notes', fontSize=8, leading=10, fontName='Helvetica'))

        table_data.append([
            Paragraph(f'<b>{num}.</b> {desc}', item_style),
            impl_p,
            maint_p,
            notes_p,
        ])

    col_widths_checklist = [3.1*inch, 1.0*inch, 1.0*inch, 1.2*inch]
    checklist_t = Table(table_data, colWidths=col_widths_checklist, repeatRows=1)

    ts = TableStyle([
        # Header
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        # All cells
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ])
    # Alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0,i), (-1,i), colors.Color(0.97, 0.97, 0.97))

    checklist_t.setStyle(ts)
    story.append(checklist_t)

    story.append(Spacer(1, 10))
    story.append(Paragraph('<b>Comments:</b>', normal))
    story.append(Spacer(1, 3))

    # Comments box
    comments_t = Table(
        [[Paragraph(comments or '', ParagraphStyle('comments', fontSize=9, leading=12, fontName='Helvetica'))]],
        colWidths=[W], rowHeights=[max(60, 12 * (comments.count('\n') + 1) + 20) if comments else 60]
    )
    comments_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(comments_t)

    story.append(Spacer(1, 8))
    story.append(Paragraph(f'Report generated: {generated_at}', footer_style))

    doc.build(story)
