import zoneinfo
from datetime import datetime

from django.template.loader import render_to_string


def generate_dpa_pdf(full_name: str, dpa_accepted_at: datetime) -> bytes:
    from weasyprint import HTML

    dt_berlin = dpa_accepted_at.astimezone(zoneinfo.ZoneInfo('Europe/Berlin'))
    accepted_at_str = dt_berlin.strftime('%d.%m.%Y, %H:%M:%S Uhr (%Z)')

    html = HTML(
        string=render_to_string(
            'dpa/dpa_pdf.html',
            {
                'full_name': full_name,
                'dpa_accepted_at': accepted_at_str,
            },
        )
    )
    return html.write_pdf()
