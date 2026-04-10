"""
PDF Generator for SWPPP Inspection Report
Matches the original WeasyPrint quality using ReportLab canvas-level drawing.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SIG_PATH = os.path.join(_SCRIPT_DIR, 'static', 'signature.png')

PAGE_W, PAGE_H = letter
L_MARGIN = 0.75 * inch
R_MARGIN = 0.75 * inch
T_MARGIN = 0.65 * inch
B_MARGIN = 0.65 * inch
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN  # ~7.0 inch


# ── Custom Flowables ──────────────────────────────────────────────────────────

class CheckBox(Flowable):
    """Drawn checkbox — filled square or empty square."""
    def __init__(self, checked=False, size=9):
        super().__init__()
        self.checked = checked
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        c = self.canv
        c.setLineWidth(0.8)
        c.setStrokeColor(colors.black)
        if self.checked:
            c.setFillColor(colors.black)
            c.rect(0, 0, self.size, self.size, stroke=1, fill=1)
        else:
            c.setFillColor(colors.white)
            c.rect(0, 0, self.size, self.size, stroke=1, fill=1)


class InlineCheckLabel(Flowable):
    """A single-row inline element: [checkbox] [space] [label text]."""
    def __init__(self, label, checked=False, cb_size=9, font='Helvetica', font_size=10, leading=13):
        super().__init__()
        self.label = label
        self.checked = checked
        self.cb_size = cb_size
        self.font = font
        self.font_size = font_size
        self.leading = leading
        self.width = CONTENT_W
        self.height = leading

    def draw(self):
        c = self.canv
        # Draw checkbox
        c.setLineWidth(0.8)
        c.setStrokeColor(colors.black)
        if self.checked:
            c.setFillColor(colors.black)
        else:
            c.setFillColor(colors.white)
        cb_y = (self.height - self.cb_size) / 2
        c.rect(0, cb_y, self.cb_size, self.cb_size, stroke=1, fill=1)
        # Draw label
        c.setFillColor(colors.black)
        c.setFont(self.font, self.font_size)
        c.drawString(self.cb_size + 4, cb_y + 1, self.label)


class UnderlinedField(Flowable):
    """Label (bold) + value text + underline extending to right margin."""
    def __init__(self, label, value='', label_width=None, font_size=10):
        super().__init__()
        self.label = label
        self.value = value or ''
        self.label_width = label_width
        self.font_size = font_size
        self.width = CONTENT_W
        self.height = font_size + 8

    def draw(self):
        c = self.canv
        fs = self.font_size
        y = 2  # baseline

        # Bold label
        c.setFont('Helvetica-Bold', fs)
        c.setFillColor(colors.black)
        c.drawString(0, y, self.label)
        label_w = c.stringWidth(self.label, 'Helvetica-Bold', fs)

        # Value text
        c.setFont('Helvetica', fs)
        val_x = label_w + 4
        c.drawString(val_x, y, self.value)

        # Underline from end of label to right edge
        underline_x = val_x
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.black)
        c.line(underline_x, y - 1, self.width, y - 1)


# ── Styles ────────────────────────────────────────────────────────────────────

def _styles():
    normal = ParagraphStyle('normal', fontSize=10, leading=14, fontName='Helvetica')
    bold   = ParagraphStyle('bold',   fontSize=10, leading=14, fontName='Helvetica-Bold')
    small  = ParagraphStyle('small',  fontSize=8.5, leading=12, fontName='Helvetica')
    italic = ParagraphStyle('italic', fontSize=10, leading=14, fontName='Helvetica-Oblique')
    title1 = ParagraphStyle('title1', fontSize=16, leading=20, fontName='Helvetica-Bold', alignment=TA_CENTER)
    title2 = ParagraphStyle('title2', fontSize=14, leading=18, fontName='Helvetica-Bold', alignment=TA_CENTER)
    section_hdr = ParagraphStyle('section_hdr', fontSize=11, leading=15, fontName='Helvetica-Bold')
    cert_text = ParagraphStyle('cert_text', fontSize=9.5, leading=14, fontName='Helvetica-Oblique',
                               alignment=TA_JUSTIFY, leftIndent=6, rightIndent=6)
    footer_style = ParagraphStyle('footer', fontSize=8, leading=11, fontName='Helvetica-Oblique',
                                  alignment=TA_CENTER, textColor=colors.grey)
    return dict(normal=normal, bold=bold, small=small, italic=italic,
                title1=title1, title2=title2, section_hdr=section_hdr,
                cert_text=cert_text, footer=footer_style)


# ── Checkbox Yes/No cell ──────────────────────────────────────────────────────

class YesNoCell(Flowable):
    """Renders ■ Yes  □ No or □ Yes  ■ No inline with drawn checkboxes."""
    def __init__(self, value, na=False, cb_size=9, font_size=9.5, cell_width=1.0*inch):
        super().__init__()
        self.value = value  # True/False/'yes'/'no'/True/False
        self.na = na
        self.cb_size = cb_size
        self.font_size = font_size
        self.width = cell_width
        self.height = 14

    def draw(self):
        c = self.canv
        fs = self.font_size
        cb = self.cb_size

        if self.na:
            c.setFont('Helvetica', fs)
            c.setFillColor(colors.grey)
            tw = c.stringWidth('N/A', 'Helvetica', fs)
            c.drawString((self.width - tw) / 2, 2, 'N/A')
            return

        # Determine checked state
        if isinstance(self.value, bool):
            yes_checked = self.value
        elif str(self.value).lower() in ('true', 'yes', '1'):
            yes_checked = True
        else:
            yes_checked = False

        no_checked = not yes_checked

        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)

        # Center the whole group
        yes_w = cb + 3 + c.stringWidth('Yes', 'Helvetica', fs)
        no_w  = cb + 3 + c.stringWidth('No',  'Helvetica', fs)
        gap   = 8
        total = yes_w + gap + no_w
        x = (self.width - total) / 2
        y_cb = (self.height - cb) / 2

        # Yes checkbox
        c.setFillColor(colors.black if yes_checked else colors.white)
        c.rect(x, y_cb, cb, cb, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont('Helvetica', fs)
        c.drawString(x + cb + 3, y_cb + 1, 'Yes')
        x += yes_w + gap

        # No checkbox
        c.setFillColor(colors.black if no_checked else colors.white)
        c.rect(x, y_cb, cb, cb, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.drawString(x + cb + 3, y_cb + 1, 'No')


# ── Main generator ────────────────────────────────────────────────────────────

def generate_swppp_pdf(form_data: dict, output_path: str):
    """Generate the SWPPP inspection report PDF from form data."""

    # Extract form data
    project_location   = form_data.get("project_location", "9561 Springs Road, Warrenton, VA 20186")
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

    S = _styles()
    W = CONTENT_W

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN,  bottomMargin=B_MARGIN,
    )

    story = []

    # ── PAGE 1 ────────────────────────────────────────────────────────────────

    # Title
    story.append(Paragraph('SWPPP Inspection Report', S['title1']))
    story.append(HRFlowable(width=W, thickness=2, color=colors.black, spaceAfter=8))

    # General Information
    story.append(Paragraph('General Information', S['section_hdr']))
    story.append(Spacer(1, 4))

    for label, value, lw in [
        ('Project Location:', project_location, None),
        ('Date of Inspection:', inspection_date, None),
        ("Inspector's Name:", inspector_name, None),
        ("Inspector's Contact Information:", inspector_contact, None),
        ('Describe current phase of construction:', construction_phase, None),
    ]:
        story.append(UnderlinedField(label, value))
        story.append(Spacer(1, 3))

    # Inspection Schedule
    story.append(Paragraph('<b>Inspection Schedule:</b>', S['normal']))
    story.append(Spacer(1, 3))

    s4  = schedule == 'every4'
    s5  = schedule == 'every5'
    smo = schedule == 'monthly'

    sched_data = [[
        _make_cb_para(s4,  'Every 4 days'),
        _make_cb_para(s5,  'Every 5 days & 24 hours after rain event'),
        _make_cb_para(smo, 'Monthly'),
        Paragraph('(w/ county inspector approval)', S['normal']),
    ]]
    sched_t = Table(sched_data, colWidths=[1.5*inch, 2.8*inch, 0.9*inch, 1.8*inch])
    sched_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sched_t)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey, spaceBefore=8, spaceAfter=6))

    # Weather Information
    story.append(Paragraph('Weather Information', S['section_hdr']))
    story.append(Spacer(1, 4))

    # Storm event question
    storm_yes_checked = bool(storm_event)
    storm_row = Table([[
        Paragraph('<b>Has there been a storm event since the last inspection?</b>', S['normal']),
        _make_cb_para(storm_yes_checked, 'Yes'),
        _make_cb_para(not storm_yes_checked, 'No'),
    ]], colWidths=[4.2*inch, 0.7*inch, 0.7*inch])
    storm_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(storm_row)
    story.append(Spacer(1, 2))
    story.append(Paragraph('<i>If yes, provide:</i>', S['italic']))
    story.append(Spacer(1, 3))

    # Storm details (always show fields, filled if storm_event)
    sd1 = storm_start_date + (' ' + storm_start_time if storm_start_time else '') if storm_event else ''
    sd2 = storm_duration if storm_event else ''
    sd3 = storm_precip if storm_event else ''

    storm_detail = Table([
        [
            Paragraph('<b>Storm Start Date &amp; Time:</b>', S['normal']),
            Paragraph(sd1, S['normal']),
            Paragraph('<b>Storm Duration (hrs):</b>', S['normal']),
            Paragraph(sd2, S['normal']),
        ],
        [
            Paragraph('<b>Approximate Amount of Precipitation (in):</b>', S['normal']),
            Paragraph(sd3, S['normal']),
            '', '',
        ],
    ], colWidths=[2.3*inch, 1.4*inch, 1.7*inch, 1.6*inch])
    storm_detail.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
        ('LINEBELOW', (3,0), (3,0), 0.5, colors.black),
        ('LINEBELOW', (1,1), (1,1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(storm_detail)
    story.append(Spacer(1, 5))

    # Weather checkboxes row 1: Clear Cloudy Rain Fog Sleet Snowing
    def wc(key):
        return bool(weather_opts.get(key, False))

    weather_keys_row1 = ['Clear', 'Cloudy', 'Rain', 'Fog', 'Sleet', 'Snowing']
    weather_cells_row1 = [Paragraph('<b>Weather at time of this inspection?</b>', S['normal'])]
    for wk in weather_keys_row1:
        weather_cells_row1.append(_make_cb_para(wc(wk), wk))

    col_w1 = [2.5*inch, 0.65*inch, 0.75*inch, 0.6*inch, 0.55*inch, 0.6*inch, 0.85*inch]
    weather_t1 = Table([weather_cells_row1], colWidths=col_w1)
    weather_t1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(weather_t1)
    story.append(Spacer(1, 3))

    # Weather row 2: High Winds + Temperature
    hw_cell = _make_cb_para(wc('High Winds'), 'High Winds')
    temp_cell = Paragraph(f'<b>Temperature:</b> {temperature}°F', S['normal'])
    other_cell = Paragraph(f'<b>Other:</b> {weather_other}' if weather_other else '', S['normal'])

    weather_t2 = Table([[hw_cell, temp_cell, other_cell]],
                       colWidths=[1.4*inch, 1.8*inch, 3.8*inch])
    weather_t2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(weather_t2)
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey, spaceBefore=8, spaceAfter=6))

    # Certification Statement box
    cert_header_style = ParagraphStyle('ch', fontSize=11, leading=15,
                                       fontName='Helvetica-BoldOblique', alignment=TA_CENTER)
    cert_inner = Paragraph(
        '\u201cI certify under penalty of law that this document and all attachments were prepared under my '
        'direction or supervision in accordance with a system designed to assure that qualified personnel '
        'properly gathered and evaluated the information submitted. Based on my inquiry of the person or '
        'persons who manage the system, or those persons directly responsible for gathering the information, '
        'the information submitted is, to the best of my knowledge and belief, true, accurate, and complete. '
        'I am aware that there are significant penalties for submitting false information, including the '
        'possibility of fine and imprisonment for knowing violations.\u201d',
        S['cert_text'])

    cert_t = Table(
        [[Paragraph('<b><i>Certification Statement</i></b>', cert_header_style)],
         [cert_inner]],
        colWidths=[W]
    )
    cert_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.5, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.Color(0.88, 0.88, 0.88)),
        ('LINEBELOW', (0,0), (0,0), 1.5, colors.black),
        ('TOPPADDING', (0,0), (0,0), 6),
        ('BOTTOMPADDING', (0,0), (0,0), 6),
        ('TOPPADDING', (0,1), (0,1), 10),
        ('BOTTOMPADDING', (0,1), (0,1), 12),
        ('LEFTPADDING', (0,1), (0,1), 8),
        ('RIGHTPADDING', (0,1), (0,1), 8),
    ]))
    story.append(cert_t)
    story.append(Spacer(1, 18))

    # Signature row
    sig_elements = []
    if os.path.exists(_SIG_PATH):
        try:
            sig_img = Image(_SIG_PATH, width=2.0*inch, height=0.65*inch)
            sig_elements.append(sig_img)
        except Exception:
            sig_elements.append(Spacer(1, 0.65*inch))
    else:
        sig_elements.append(Spacer(1, 0.65*inch))

    name_style = ParagraphStyle('name_sig', fontSize=10, leading=14, fontName='Helvetica-Bold')
    date_style = ParagraphStyle('date_sig', fontSize=10, leading=14, fontName='Helvetica-Bold')

    sig_data = [[sig_elements[0], Paragraph(inspector_name, name_style), Paragraph(inspection_date, date_style)]]
    sig_t = Table(sig_data, colWidths=[2.5*inch, 2.8*inch, 1.7*inch])
    sig_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW', (0,0), (0,0), 0.5, colors.black),
        ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
        ('LINEBELOW', (2,0), (2,0), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 2))

    label_style = ParagraphStyle('sig_lbl', fontSize=8.5, leading=11,
                                 fontName='Helvetica-Oblique', textColor=colors.black)
    sig_labels = Table([[
        Paragraph('<i>Signature of Inspector</i>', label_style),
        Paragraph('<i>Printed Name and Title</i>', label_style),
        Paragraph('<i>Date</i>', label_style),
    ]], colWidths=[2.5*inch, 2.8*inch, 1.7*inch])
    sig_labels.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sig_labels)

    # ── PAGE 2 ────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('Overall Site Issues', S['title2']))
    story.append(HRFlowable(width=W, thickness=2, color=colors.black, spaceAfter=6))
    story.append(Paragraph(
        'Below are some general site issues that should be assessed during inspections.',
        ParagraphStyle('note', fontSize=9.5, leading=13, fontName='Helvetica')))
    story.append(Spacer(1, 8))

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

    item_style = ParagraphStyle('item', fontSize=9.5, leading=13, fontName='Helvetica')
    hdr_style  = ParagraphStyle('hdr',  fontSize=9.5, leading=13, fontName='Helvetica-Bold', alignment=TA_CENTER)
    hdr_l_style = ParagraphStyle('hdr_l', fontSize=9.5, leading=13, fontName='Helvetica-Bold')

    CB_W = 1.05 * inch
    NOTE_W = 1.3 * inch
    DESC_W = W - CB_W * 2 - NOTE_W

    table_data = [[
        Paragraph('Site Activity', hdr_l_style),
        Paragraph('Implemented?', hdr_style),
        Paragraph('Maintenance?', hdr_style),
        Paragraph('Notes', hdr_style),
    ]]

    for num, desc, has_maint in site_items_def:
        item = site_items_data.get(str(num), {})
        impl  = item.get('implemented', False)
        maint = item.get('maintenance', False)
        notes = item.get('notes', '') or ''

        impl_cell  = YesNoCell(impl,  na=False,     cell_width=CB_W)
        maint_cell = YesNoCell(maint, na=not has_maint, cell_width=CB_W)
        notes_cell = Paragraph(notes, ParagraphStyle('notes_cell', fontSize=9, leading=12, fontName='Helvetica'))

        table_data.append([
            Paragraph(f'<b>{num}.</b> {desc}', item_style),
            impl_cell,
            maint_cell,
            notes_cell,
        ])

    checklist_t = Table(table_data,
                        colWidths=[DESC_W, CB_W, CB_W, NOTE_W],
                        repeatRows=1)

    ts = TableStyle([
        # Header row
        ('BACKGROUND', (0,0), (-1,0), colors.Color(0.85, 0.85, 0.85)),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        # All cells
        ('BOX', (0,0), (-1,-1), 0.75, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (1,0), (2,-1), 2),
        ('RIGHTPADDING', (1,0), (2,-1), 2),
    ])
    # Alternating row shading
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0,i), (-1,i), colors.Color(0.97, 0.97, 0.97))

    checklist_t.setStyle(ts)
    story.append(checklist_t)

    story.append(Spacer(1, 10))
    story.append(Paragraph('<b>Comments:</b>', S['normal']))
    story.append(Spacer(1, 4))

    comments_height = max(70, 14 * (comments.count('\n') + 2)) if comments else 70
    comments_t = Table(
        [[Paragraph(comments or '', ParagraphStyle('comments', fontSize=9.5, leading=13, fontName='Helvetica'))]],
        colWidths=[W], rowHeights=[comments_height]
    )
    comments_t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    # Footer — embed inside a small table below comments so it stays on page 2
    footer_t = Table(
        [[Paragraph(f'Report generated: {generated_at}', S['footer'])]],
        colWidths=[W]
    )
    footer_t.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # Keep comments + footer together on the same page
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether([comments_t, footer_t]))

    doc.build(story)


def _make_cb_para(checked, label, font_size=10):
    """Return a Table containing a drawn checkbox + label text."""
    cb = CheckBox(checked=checked, size=9)
    lbl = Paragraph(label, ParagraphStyle('cblbl', fontSize=font_size, leading=13, fontName='Helvetica'))
    t = Table([[cb, lbl]], colWidths=[12, None])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    return t
