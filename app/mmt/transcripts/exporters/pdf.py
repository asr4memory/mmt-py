"""Export a transcript as a PDF document meant to be read.

The body is one block per speaker turn and not one per segment: reading a
transcript segment by segment breaks a sentence every few seconds, and the
segment boundaries carry no meaning for a reader.
"""

from django.template.loader import render_to_string

from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.exporters.timecode import hhmmssmmm
from mmt.transcripts.exporters.turns import SpeakerTurn, speaker_turns

TEMPLATE = 'transcripts/export_pdf.html'


def export(context: ExportContext) -> bytes:
    # WeasyPrint is imported inside the function, as it is in
    # mmt/my_account/pdf.py, so that importing the registry does not pull in
    # the rendering stack.
    from weasyprint import HTML

    return HTML(string=render_html(context)).write_pdf()


def render_html(context: ExportContext) -> str:
    """The document's HTML, before WeasyPrint turns it into a PDF.

    Separate from ``export`` so that the layout can be asserted on without
    rendering a PDF.
    """
    return render_to_string(TEMPLATE, _template_context(context))


def _template_context(context: ExportContext) -> dict:
    return {
        'label': context.label,
        'project_title': context.project_title,
        'filename': context.filename,
        'created_at': context.created_at,
        'language': context.transcript.language,
        'turns': [
            {
                'time': _hhmmss(turn.start),
                'speaker': _speaker_name(turn),
                'text': turn.text,
            }
            for turn in speaker_turns(context.transcript)
        ],
    }


def _speaker_name(turn: SpeakerTurn) -> str | None:
    """The speaker's name, falling back to the speaker's id when the name is
    empty, and None for a turn without a speaker."""
    if turn.speaker is None:
        return None
    return turn.speaker.name or turn.speaker.id


def _hhmmss(seconds: float) -> str:
    """The turn's start time without milliseconds, which a reader of the
    document has no use for."""
    return hhmmssmmm(seconds).partition('.')[0]
