"""
PDF Generator for SWPPP Inspection Report
Uses WeasyPrint (HTML-to-PDF) with CSS-based checkboxes for reliable rendering.
"""

import base64
import os
from weasyprint import HTML
from datetime import datetime

# ── Load signature image as base64 for PDF embedding ──────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SIG_PATH = os.path.join(_SCRIPT_DIR, 'static', 'signature.png')
try:
    with open(_SIG_PATH, 'rb') as _f:
        _SIG_B64 = base64.b64encode(_f.read()).decode()
    SIGNATURE_IMG = f'data:image/png;base64,{_SIG_B64}'
except FileNotFoundError:
    SIGNATURE_IMG = ''


def _box(checked: bool) -> str:
    """Return an HTML span for a filled (black) or empty checkbox square."""
    cls = 'cb-checked' if checked else 'cb-unchecked'
    return f'<span class="{cls}"></span>'


def cb(value: bool, label: str) -> str:
    """Return a single checkbox + label."""
    return f'{_box(value)} {label}'


def cb_yes_no(value: str) -> str:
    """Return Yes/No checkbox pair HTML."""
    return f'{_box(value == "yes")} Yes &nbsp;&nbsp; {_box(value == "no")} No'


def generate_swppp_pdf(form_data: dict, output_path: str):
    """Generate the SWPPP inspection report PDF from form data."""

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

    # ── Inspection schedule checkboxes ─────────────────────────────────────────
    sched_4       = _box(schedule == "every4")
    sched_5       = _box(schedule == "every5")
    sched_monthly = _box(schedule == "monthly")

    # ── Storm event checkboxes ─────────────────────────────────────────────────
    storm_yes_sym = _box(bool(storm_event))
    storm_no_sym  = _box(not bool(storm_event))

    # Storm detail always shown; blank when no storm
    storm_detail_html = f"""
        <div class="storm-detail">
          <p class="if-yes">If yes, provide:</p>
          <table class="storm-table">
            <tr>
              <td class="label"><b>Storm Start Date &amp; Time:</b></td>
              <td class="value underline">{storm_start_date} {storm_start_time}</td>
              <td class="label"><b>Storm Duration (hrs):</b></td>
              <td class="value underline">{storm_duration}</td>
            </tr>
            <tr>
              <td class="label"><b>Approximate Amount of Precipitation (in):</b></td>
              <td class="value underline">{storm_precip}</td>
              <td></td><td></td>
            </tr>
          </table>
        </div>
        """

    # ── Weather checkboxes ─────────────────────────────────────────────────────
    def wc(key):
        return _box(bool(weather_opts.get(key, False)))

    # ── Overall Site Issues table rows ─────────────────────────────────────────
    site_items_def = [
        (1,  "Is permit and SWPPP contact info posted near the entrance of the project site?", True),
        (2,  "Is the SWPPP up to date, available on site, and properly maintained?", False),
        (3,  "Are all inactive disturbed areas or slopes stabilized? If so, with what?", True),
        (4,  "Natural resources (wetlands, trees, etc.) protected with perimeter controls (silt fence, etc.)?", True),
        (5,  "Are porta-johns placed away from water sources, free of leaks and properly contained?", True),
        (6,  "Are perimeter controls (silt fence, etc.) adequately installed? Being maintained?", True),
        (7,  "Are discharge points and receiving waters free of any sediment deposits?", True),
        (8,  "Are all storm drain inlets properly protected?", True),
        (9,  "All stockpiles/construction materials located in approved areas &amp; protected from erosion?", True),
        (10, "Is construction entrance stopping sediment from being tracked onto paved roads?", True),
        (11, "Is all trash being collected and being properly disposed of in dumpsters?", True),
        (12, "Are washout facilities (paint, concrete, etc.) present, clearly marked, and maintained?", True),
        (13, "Are vehicle and equipment fueling, cleaning, and maintenance areas free of spills, leaks, or other harmful material?", True),
        (14, "Are potential contaminant materials stored inside or under cover?", True),
        (15, "Are dumpsters on site being covered at the end of each day and during rain events?", True),
        (16, "(Other)", True),
    ]

    rows_html = ""
    for i, (num, desc, has_maint) in enumerate(site_items_def):
        item = site_items_data.get(str(num), {})
        impl  = item.get("implemented", "")
        maint = item.get("maintenance", "")
        notes = item.get("notes", "")
        row_class = "row-alt" if i % 2 == 1 else ""

        impl_html = cb_yes_no(impl)
        if has_maint:
            maint_html = cb_yes_no(maint)
        else:
            maint_html = "<span style='color:#999'>N/A</span>"

        rows_html += f"""
        <tr class="{row_class}">
          <td class="activity"><b>{num}.</b> {desc}</td>
          <td class="yn-cell">{impl_html}</td>
          <td class="yn-cell">{maint_html}</td>
          <td class="notes-cell">{notes}</td>
        </tr>"""

    # ── Full HTML document ─────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: letter;
    margin: 0.55in 0.65in 0.55in 0.65in;
  }}
  @font-face {{
    font-family: 'NotoSans';
    src: url('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf');
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'NotoSans', Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: #000;
    line-height: 1.3;
  }}

  /* ── Checkbox styles ── */
  .cb-checked {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border: 1.5px solid #000;
    background: #000;
    vertical-align: middle;
    margin-right: 2px;
  }}
  .cb-unchecked {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border: 1.5px solid #000;
    background: white;
    vertical-align: middle;
    margin-right: 2px;
  }}

  /* ── Title ── */
  h1.report-title {{
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    margin: 0 0 4px 0;
    padding: 0;
  }}
  hr.thick {{ border: none; border-top: 2px solid #000; margin: 4px 0 8px 0; }}
  hr.thin  {{ border: none; border-top: 1px solid #888; margin: 6px 0 6px 0; }}

  /* ── Section headers ── */
  h2.section {{
    font-size: 11pt;
    font-weight: bold;
    margin: 8px 0 4px 0;
  }}

  /* ── Field rows ── */
  .field-row {{
    display: flex;
    align-items: flex-end;
    margin-bottom: 4px;
    gap: 6px;
  }}
  .field-label {{
    font-weight: bold;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .field-value {{
    border-bottom: 1px solid #000;
    flex: 1;
    min-width: 60px;
    padding-bottom: 1px;
  }}
  .field-row-2col {{
    display: flex;
    gap: 16px;
    margin-bottom: 4px;
  }}
  .field-row-2col .col {{
    display: flex;
    align-items: flex-end;
    gap: 6px;
    flex: 1;
  }}

  /* ── Schedule row ── */
  .sched-row {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 4px;
  }}
  .sched-option {{
    display: flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }}

  /* ── Storm detail table ── */
  .storm-detail {{ margin: 4px 0; }}
  .if-yes {{ font-style: italic; font-size: 8.5pt; margin: 2px 0; }}
  table.storm-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
  }}
  table.storm-table td {{ padding: 2px 4px; vertical-align: bottom; }}
  table.storm-table td.label {{ font-weight: bold; white-space: nowrap; width: 30%; }}
  table.storm-table td.value {{ border-bottom: 1px solid #000; width: 20%; }}

  /* ── Weather row ── */
  .weather-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 0;
    flex-wrap: wrap;
  }}
  .weather-option {{
    display: flex;
    align-items: center;
    gap: 3px;
    white-space: nowrap;
  }}

  /* ── Certification box ── */
  .cert-box {{
    border: 2px solid #000;
    margin: 8px 0 10px 0;
  }}
  .cert-header {{
    background: #d3d3d3;
    text-align: center;
    font-size: 11pt;
    padding: 5px 8px;
    border-bottom: 2px solid #000;
  }}
  .cert-text {{
    font-style: italic;
    font-size: 9pt;
    text-align: justify;
    margin: 8px 12px 10px 12px;
    line-height: 1.5;
  }}

  /* ── Signature section ── */
  .sig-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
  }}
  .sig-table td {{
    padding: 0;
    vertical-align: bottom;
  }}
  .sig-td-left  {{ width: 38%; padding-right: 16px; }}
  .sig-td-mid   {{ width: 40%; padding-right: 16px; }}
  .sig-td-right {{ width: 22%; }}
  .sig-img {{
    max-height: 55px;
    max-width: 180px;
    object-fit: contain;
    display: block;
    margin-bottom: 0;
  }}
  .sig-line-full {{
    border-bottom: 1px solid #000;
    height: 1px;
    width: 100%;
    display: block;
  }}
  .sig-label-text {{
    font-size: 8pt;
    font-style: italic;
    margin-top: 3px;
    display: block;
  }}
  .sig-filled {{
    font-size: 9pt;
    font-weight: bold;
    margin-top: 2px;
    display: block;
  }}

  /* ── Page 2 ── */
  .page-break {{ page-break-before: always; }}
  h1.page2-title {{
    text-align: center;
    font-size: 13pt;
    font-weight: bold;
    margin: 0 0 4px 0;
  }}

  /* ── Checklist table ── */
  table.checklist {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-top: 6px;
  }}
  table.checklist th {{
    background: #d3d3d3;
    font-weight: bold;
    border: 1px solid #000;
    padding: 4px 5px;
    text-align: center;
    font-size: 8.5pt;
  }}
  table.checklist th.activity-h {{ text-align: left; }}
  table.checklist td {{
    border: 1px solid #000;
    padding: 4px 5px;
    vertical-align: middle;
  }}
  table.checklist td.activity {{ font-size: 8.5pt; }}
  table.checklist td.yn-cell {{
    text-align: center;
    white-space: nowrap;
    width: 13%;
  }}
  table.checklist td.notes-cell {{ width: 18%; font-size: 8pt; }}
  tr.row-alt td {{ background: #f8f8f8; }}

  /* ── Comments ── */
  .comments-box {{
    border: 1px solid #000;
    min-height: 60px;
    padding: 5px;
    margin-top: 4px;
    font-size: 9pt;
  }}
  .footer {{
    text-align: center;
    font-size: 7.5pt;
    color: #666;
    font-style: italic;
    margin-top: 10px;
  }}
</style>
</head>
<body>

<!-- ═══════════════════ PAGE 1 ═══════════════════ -->
<h1 class="report-title">SWPPP Inspection Report</h1>
<hr class="thick">

<!-- General Information -->
<h2 class="section">General Information</h2>

<div class="field-row">
  <span class="field-label">Project Location:</span>
  <span class="field-value">{project_location}</span>
</div>

<div class="field-row">
  <span class="field-label">Date of Inspection:</span>
  <span class="field-value">{inspection_date}</span>
</div>

<div class="field-row">
  <span class="field-label">Inspector's Name:</span>
  <span class="field-value">{inspector_name}</span>
</div>

<div class="field-row">
  <span class="field-label">Inspector's Contact Information:</span>
  <span class="field-value">{inspector_contact}</span>
</div>

<div class="field-row">
  <span class="field-label">Describe current phase of construction:</span>
  <span class="field-value">{construction_phase}</span>
</div>

<div style="margin-bottom:4px;">
  <span class="field-label">Inspection Schedule:</span><br>
  <div class="sched-row" style="margin-top:3px;">
    <span class="sched-option">{sched_4} Every 4 days</span>
    <span class="sched-option">{sched_5} Every 5 days &amp; 24 hours after rain event</span>
    <span class="sched-option">{sched_monthly} Monthly<br><span style="font-size:8pt;padding-left:14px;">(w/ county inspector approval)</span></span>
  </div>
</div>

<hr class="thin">

<!-- Weather Information -->
<h2 class="section">Weather Information</h2>

<div class="field-row" style="gap:16px;">
  <span class="field-label">Has there been a storm event since the last inspection?</span>
  <span style="margin-left:8px; display:flex; align-items:center; gap:6px;">
    {storm_yes_sym} Yes &nbsp;&nbsp; {storm_no_sym} No
  </span>
</div>

{storm_detail_html}

<div class="weather-row">
  <span class="field-label">Weather at time of this inspection?</span>
  <span class="weather-option">{wc('Clear')} Clear</span>
  <span class="weather-option">{wc('Cloudy')} Cloudy</span>
  <span class="weather-option">{wc('Rain')} Rain</span>
  <span class="weather-option">{wc('Fog')} Fog</span>
  <span class="weather-option">{wc('Sleet')} Sleet</span>
  <span class="weather-option">{wc('Snowing')} Snowing</span>
  <span class="weather-option">{wc('High Winds')} High Winds</span>
  <span style="margin-left:8px;"><b>Temperature:</b> {temperature}</span>
</div>
{'<div style="font-size:9pt;margin-top:2px;"><b>Other:</b> ' + weather_other + '</div>' if weather_other else ''}

<hr class="thin">

<!-- Certification Statement -->
<div class="cert-box">
  <div class="cert-header"><em><strong>Certification Statement</strong></em></div>
  <p class="cert-text">
    &#8220;I certify under penalty of law that this document and all attachments were prepared under my
    direction or supervision in accordance with a system designed to assure that qualified personnel
    properly gathered and evaluated the information submitted. Based on my inquiry of the person or
    persons who manage the system, or those persons directly responsible for gathering the information,
    the information submitted is, to the best of my knowledge and belief, true, accurate, and complete.
    I am aware that there are significant penalties for submitting false information, including the
    possibility of fine and imprisonment for knowing violations.&#8221;
  </p>
</div>

<!-- Signature row: Left=Signature, Center=Printed Name & Title, Right=Date -->
<table class="sig-table">
  <tr>
    <td class="sig-td-left">
      {'<img src="' + SIGNATURE_IMG + '" class="sig-img" alt="Signature">' if SIGNATURE_IMG else '<div style="height:55px;"></div>'}
      <span class="sig-line-full"></span>
      <span class="sig-label-text"><em>Signature of Inspector</em></span>
    </td>
    <td class="sig-td-mid">
      <span class="sig-filled">{inspector_name}</span>
      <span class="sig-line-full"></span>
      <span class="sig-label-text"><em>Printed Name and Title</em></span>
    </td>
    <td class="sig-td-right">
      <span class="sig-filled">{inspection_date}</span>
      <span class="sig-line-full"></span>
      <span class="sig-label-text"><em>Date</em></span>
    </td>
  </tr>
</table>


<!-- ═══════════════════ PAGE 2 ═══════════════════ -->
<div class="page-break"></div>

<h1 class="page2-title">Overall Site Issues</h1>
<hr class="thick">
<p style="font-size:8.5pt;margin:4px 0 6px 0;">Below are some general site issues that should be assessed during inspections.</p>

<table class="checklist">
  <thead>
    <tr>
      <th class="activity-h">Site Activity</th>
      <th>Implemented?</th>
      <th>Maintenance?</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<div style="margin-top:10px;">
  <b>Comments:</b>
  <div class="comments-box">{comments}</div>
</div>

<div class="footer">Report generated: {generated_at}</div>

</body>
</html>"""

    HTML(string=html).write_pdf(output_path)
