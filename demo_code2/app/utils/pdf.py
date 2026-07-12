"""
PDF Export Module for the Sing Yin Study Prefect Duty Roster System.

Generates a clean, professional, bilingual (Chinese + English)
weekly duty roster PDF using WeasyPrint.
"""

from datetime import date
from pathlib import Path
from typing import List, Optional

from models.enums import Weekday, Room
from models.roster import WeeklyRoster

WEEKDAY_ZH = {
    Weekday.MON: "星期一",
    Weekday.TUE: "星期二",
    Weekday.WED: "星期三",
    Weekday.THU: "星期四",
    Weekday.FRI: "星期五",
}

ROOM_LABELS = {
    Room.ROOM_302: "Room 302 (Study Room)",
    Room.ROOM_303: "Room 303 (HW Completion)",
    Room.ROOM_202: "Room 202 (F1 Study Group)",
}


def generate_roster_pdf(roster: WeeklyRoster, prefects: list = None) -> bytes:
    """Generate a professional A4 PDF of the weekly duty roster.

    Args:
        roster: A validated WeeklyRoster with room assignments.
        prefects: Optional list of Prefect objects/dicts for name lookup.

    Returns:
        PDF bytes ready for download.
    """
    prefects = prefects or []
    # Build name lookup: English name -> {name_zh, form, class}
    names = {}
    for p in prefects:
        n = p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")
        if n:
            names[n] = {
                "name_zh": p.get("name_zh", "") if isinstance(p, dict) else getattr(p, "name_zh", ""),
                "form": p.get("form", "") if isinstance(p, dict) else getattr(p, "form", ""),
                "class_name": p.get("class_name", "") if isinstance(p, dict) else getattr(p, "class_name", ""),
            }

    def cell(name: str) -> str:
        """Format a name cell for the table."""
        if not name:
            return ""
        info = names.get(name, {})
        zh = info.get("name_zh", "")
        form = info.get("form", "")
        cls = info.get("class_name", "")
        form_name = form.name if hasattr(form, "name") else str(form)
        if zh:
            return f"{name}<br/><small>{zh} {form_name}{cls}</small>"
        return name

    def room_to_rows(room: Room) -> list:
        """Build table rows for a given room across 5 weekdays."""
        rows = []
        for day in Weekday:
            daily = roster.days.get(day)
            assigned = daily.room_assignments.get(room, []) if daily else []
            if len(assigned) == 0:
                rows.append([WEEKDAY_ZH[day], "—", ""])
            elif len(assigned) == 1:
                rows.append([WEEKDAY_ZH[day], cell(assigned[0]), ""])
            else:
                for i, name in enumerate(assigned):
                    rows.append([
                        WEEKDAY_ZH[day] if i == 0 else "",
                        cell(name),
                        f"Slot {i+1}" if len(assigned) > 1 else "",
                    ])
        return rows

    def ahp_rows() -> list:
        """Build table rows for AHP assignments."""
        rows = []
        for day in Weekday:
            daily = roster.days.get(day)
            ahp = daily.ahp_assignment if daily else ""
            ahp_name = ahp.name if hasattr(ahp, "name") else str(ahp) if ahp else ""
            rows.append([WEEKDAY_ZH[day], cell(ahp_name)])
        return rows

    # Build HTML tables
    def build_room_table(room: Room, label: str) -> str:
        rows = room_to_rows(room)
        if not rows:
            return ""
        header = '<tr><th colspan="2" style="background:#0F766E;color:white;padding:8px;text-align:left;">{}</th></tr>'.format(label)
        body = ""
        for r in rows:
            body += '<tr><td style="padding:6px 8px;border-bottom:1px solid #E2E8F0;">{}</td><td style="padding:6px 8px;border-bottom:1px solid #E2E8F0;">{}</td></tr>'.format(r[0], r[1])
        return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">{}{}</table>'.format(header, body)

    def build_ahp_table() -> str:
        rows = ahp_rows()
        header = '<tr><th style="background:#D4AF37;color:#1A1A2E;padding:8px;text-align:left;">AHP (Assistant Head Prefect) Assignments</th><th style="background:#D4AF37;color:#1A1A2E;padding:8px;text-align:left;"></th></tr>'
        body = ""
        for r in rows:
            body += '<tr><td style="padding:6px 8px;border-bottom:1px solid #E2E8F0;">{}</td><td style="padding:6px 8px;border-bottom:1px solid #E2E8F0;">{}</td></tr>'.format(r[0], r[1])
        return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">{}{}</table>'.format(header, body)

    week_start = roster.week_start
    week_end = roster.week_end if hasattr(roster, "week_end") else ""
    week_label = f"{week_start}" + (f" — {week_end}" if week_end else "")

    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head><meta charset="utf-8">
<style>
  @page {{ size: A4 portrait; margin: 1.8cm; }}
  body {{
    font-family: "Noto Sans CJK HK", "Noto Sans TC", "DejaVu Sans", system-ui, sans-serif;
    color: #1E293B;
    font-size: 13px;
    line-height: 1.5;
  }}
  .header {{
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 3px solid #0F766E;
  }}
  .header h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #0F766E;
    margin: 0 0 4px 0;
  }}
  .header .sub {{
    font-size: 12px;
    color: #64748B;
  }}
  .header .verse {{
    font-size: 10px;
    color: #D4AF37;
    font-style: italic;
    margin-top: 4px;
  }}
  h2 {{
    font-size: 15px;
    color: #0F766E;
    margin: 16px 0 8px 0;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 4px;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
  th {{ padding: 8px 10px; text-align: left; font-weight: 600; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #F1F5F9; }}
  small {{ font-size: 10px; color: #64748B; }}
  .footer {{
    margin-top: 24px;
    padding-top: 8px;
    border-top: 1px solid #E2E8F0;
    font-size: 9px;
    color: #94A3B8;
    text-align: center;
  }}
</style></head>
<body>

<div class="header">
  <div style="text-align:center;margin-bottom:12px;"><img src="file:///D:/code_v2/logo.png" style="max-height:60px;" alt="School Logo"></div><h1>Sing Yin Secondary School</h1>
  <div class="sub">Study Prefect Duty Roster</div>
  <div class="sub">{week_label}</div>
  <div class="verse">"Whoever wants to become great among you must be your servant." — Mark 10:43</div>
</div>

<h2>AHP (Assistant Head Prefect) Assignments</h2>
{build_ahp_table()}

<h2>Room Duty Assignments</h2>
{build_room_table(Room.ROOM_302, ROOM_LABELS[Room.ROOM_302])}
{build_room_table(Room.ROOM_303, ROOM_LABELS[Room.ROOM_303])}
{build_room_table(Room.ROOM_202, ROOM_LABELS[Room.ROOM_202])}

<div class="footer">
  Generated by Sing Yin Study Prefect Duty Roster System — {date.today().strftime("%Y-%m-%d")}<br/>
  Professional Teal Design System v3.0
</div>

</body></html>"""

    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        raise RuntimeError(
            "WeasyPrint is required for PDF generation. "
            "Install it with: pip install weasyprint"
        )




def generate_roster_html(roster, prefects=None):
    """Generate a styled HTML roster with Professional Teal design."""
    from datetime import date
    prefects = prefects or []
    names = {}
    for p in prefects:
        n = p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")
        if n:
            names[n] = p.get("name_zh", "") if isinstance(p, dict) else getattr(p, "name_zh", "")

    def hcell(name):
        if not name: return ""
        zh = names.get(name, "")
        return name + (" (" + zh + ")" if zh else "")

    week_start = roster.week_start
    css = """@page { size: A4 portrait; margin: 1.5cm; }
body { font-family: sans-serif; color: #1E293B; font-size: 13px; }
.header { text-align: center; border-bottom: 3px solid #0F766E; padding-bottom: 12px; margin-bottom: 16px; }
.header h1 { font-size: 20px; color: #0F766E; margin: 0 0 4px 0; }
.header .sub { font-size: 12px; color: #64748B; }
.header .verse { font-size: 10px; color: #D4AF37; font-style: italic; }
h2 { font-size: 15px; color: #0F766E; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
th { background: #0F766E; color: white; padding: 8px 10px; text-align: left; }
td { padding: 6px 10px; border-bottom: 1px solid #F1F5F9; }
.footer { margin-top: 24px; border-top: 1px solid #E2E8F0; padding-top: 8px; font-size: 9px; color: #94A3B8; text-align: center; }"""

    html = '<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>Roster ' + str(week_start) + '</title><style>' + css + '</style></head><body>'
    html += '<div class="header"><h1>Sing Yin Secondary School</h1>'
    html += '<div class="sub">Study Prefect Duty Roster</div>'
    html += '<div class="sub">' + str(week_start) + '</div>'
    html += '<div class="verse">"Whoever wants to become great among you must be your servant." - Mark 10:43</div></div>'
    html += '<h2>Roster Assignments</h2>'
    html += '<table><tr><th>Day</th><th>Room</th><th>Prefect</th></tr>'

    from models.enums import Room as _Room
    room_list = [(_Room.ROOM_302, "Room 302"), (_Room.ROOM_303, "Room 303"), (_Room.ROOM_202, "Room 202")]
    for day_raw in roster.days:
        daily = roster.days[day_raw]
        day_name = day_raw.value if hasattr(day_raw, "value") else str(day_raw)
        for room_enum, room_label in room_list:
            assigned = []
            if hasattr(daily, "room_assignments"):
                assigned = daily.room_assignments.get(room_enum, [])
                if not assigned:
                    # Try string key fallback (backward compatibility)
                    for k, v in daily.room_assignments.items():
                        if hasattr(k, "value") and k == room_enum:
                            assigned = v
                            break
                        elif str(k) == str(room_enum):
                            assigned = v
                            break
            # Check if room is closed on this day
            if day_raw in room_enum.closed_days:
                html += "<tr><td>" + day_name + "</td><td>" + room_label + "</td><td><em>Closed</em></td></tr>"
                continue
            if assigned:
                for name in assigned:
                    if name and name.strip() and name.strip() != "[ON LEAVE]":
                        html += "<tr><td>" + day_name + "</td><td>" + room_label + "</td><td>" + hcell(name) + "</td></tr>"
                    elif name and "[ON LEAVE]" in name:
                        html += "<tr><td>" + day_name + "</td><td>" + room_label + "</td><td><em>[ON LEAVE]</em></td></tr>"

    html += '</table>'
    html += '<div class="footer">Generated by Sing Yin Study Prefect Duty Roster System - ' + str(date.today()) + '<br/>Professional Teal Design System v3.1</div>'
    html += '</body></html>'
    return html.encode("utf-8")

def generate_roster_pdf_bytes(roster: WeeklyRoster, prefects: list = None) -> Optional[bytes]:
    """Safe wrapper that returns None instead of raising."""
    try:
        return generate_roster_pdf(roster, prefects)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def generate_service_certificate(prefect_name: str, role: str = "Study Prefect",
                                  academic_year: str = "2026-2027") -> bytes:
    """Generate a simple service certificate PDF for a prefect."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<style>
  @page {{ size: A4 landscape; margin: 2cm; }}
  body {{
    font-family: "Noto Sans CJK", "Noto Sans TC", "DejaVu Sans", sans-serif;
    text-align: center; color: #1E293B;
  }}
  .cert {{
    border: 4px double #0F766E; border-radius: 16px;
    padding: 48px 32px; max-width: 700px; margin: 0 auto;
  }}
  .cert h1 {{ font-size: 28px; color: #0F766E; margin-bottom: 8px; }}
  .cert .sub {{ font-size: 14px; color: #64748B; margin-bottom: 32px; }}
  .cert .name {{ font-size: 32px; font-weight: 700; color: #0F766E; margin: 24px 0 8px; }}
  .cert .role {{ font-size: 18px; color: #D4AF37; margin-bottom: 32px; }}
  .cert .body {{ font-size: 14px; color: #64748B; line-height: 1.8; max-width: 500px; margin: 0 auto 32px; }}
  .cert .footer {{ font-size: 11px; color: #94A3B8; margin-top: 40px; }}
  .seal {{ font-size: 80px; color: #D4AF37; opacity: 0.15; position: absolute; }}
</style></head>
<body>
  <div class="cert">
    <div style="text-align:center;margin-bottom:12px;"><img src="file:///D:/code_v2/logo.png" style="max-height:60px;" alt="School Logo"></div><h1>Sing Yin Secondary School</h1>
    <div class="sub">Study Prefect Team</div>
    <div class="sub">Certificate of Service</div>
    <div class="name">{prefect_name}</div>
    <div class="role">{role}</div>
    <div class="body">
      This certificate is awarded in recognition of your dedicated service
      as a Study Prefect during the {academic_year} academic year.
      Your commitment to fairness, responsibility, and servant leadership
      has made a meaningful contribution to the school community.
    </div>
    <div class="footer">
      Head Study Prefect | Sing Yin Secondary School | {academic_year}
    </div>
  </div>
</body></html>"""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except (ImportError, OSError):
        return html.encode("utf-8")
