"""Export as PDF: one block per speaker turn, for a person who reads."""

from datetime import datetime

from django.template.loader import render_to_string

from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.timecode import hhmmss
from mmt.transcripts.exporters.turns import speaker_turns
from mmt.transcripts.mmt_schema import Transcript


def export_to_pdf(
    transcript: Transcript,
    *,
    label: str,
    project_title: str,
    filename: str,
    created_at: datetime,
) -> bytes:
    # Imported here, so that importing the views does not load the rendering
    # stack.
    from weasyprint import HTML

    html = render_pdf_html(
        transcript,
        label=label,
        project_title=project_title,
        filename=filename,
        created_at=created_at,
    )
    return HTML(string=html).write_pdf()


def render_pdf_html(
    transcript: Transcript,
    *,
    label: str,
    project_title: str,
    filename: str,
    created_at: datetime,
) -> str:
    """The HTML document the PDF is rendered from."""
    speaker_labels = speaker_labels_by_id(transcript)
    turns = [
        {
            'time': hhmmss(turn.start),
            'speaker': speaker_labels[turn.speaker.id] if turn.speaker else None,
            'text': turn.text,
        }
        for turn in speaker_turns(transcript)
    ]

    return render_to_string(
        'transcripts/export_pdf.html',
        {
            'label': label,
            'project_title': project_title,
            'filename': filename,
            'created_at': created_at,
            'language': transcript.language,
            'turns': turns,
        },
    )
