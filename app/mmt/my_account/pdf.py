from django.template.loader import render_to_string


def generate_dpa_pdf(full_name: str, dpa_accepted_at: str) -> bytes:
    from weasyprint import HTML

    html = HTML(
        string=render_to_string(
            'dpa/dpa_pdf.html',
            {
                'full_name': full_name,
                'dpa_accepted_at': dpa_accepted_at,
            },
        )
    )
    return html.write_pdf()
