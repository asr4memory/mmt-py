"""Export a transcript as WebVTT subtitles.

One segment becomes one cue and its text is emitted on one line, however long
the segment is. Splitting a long segment into readable cues needs a rule about
line length, reading speed and cue duration, which is its own feature.
"""

from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.exporters.timecode import hhmmssmmm


def export(context: ExportContext) -> bytes:
    transcript = context.transcript
    labels = {speaker.id: speaker.name or speaker.id for speaker in transcript.speakers}

    # The header, then one blank line before the first cue.
    lines = ['WEBVTT', '']
    for segment in transcript.segments:
        # Cues carry no identifier line. VTT allows one, but no player requires
        # it and leaving it out keeps the file smaller.
        lines.append(f'{hhmmssmmm(segment.start)} --> {hhmmssmmm(segment.end)}')

        text = _escape(' '.join(word.word for word in segment.words))
        if segment.speakerId is not None:
            text = f'<v {_escape(labels[segment.speakerId])}>{text}'
        lines.append(text)

        lines.append('')

    return '\n'.join(lines).encode()


def _escape(text: str) -> str:
    """Escape the three characters that are markup in VTT cue text.

    The ampersand is replaced first, so that the ampersands introduced by the
    two replacements after it are not escaped a second time.
    """
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
