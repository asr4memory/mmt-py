"""Export a transcript as SubRip subtitles.

One segment becomes one numbered block and its text is emitted on one line,
however long the segment is; see the note on cue splitting in ``vtt.py``.

Nothing is escaped. SubRip text is plain text, and the few players that read
HTML tags in it are not a reason to alter the transcript's characters.
"""

from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.exporters.timecode import hhmmssmmm


def export(context: ExportContext) -> bytes:
    transcript = context.transcript
    labels = {speaker.id: speaker.name or speaker.id for speaker in transcript.speakers}

    lines = []
    for number, segment in enumerate(transcript.segments, start=1):
        lines.append(str(number))
        lines.append(
            f'{hhmmssmmm(segment.start, millisecond_separator=",")} --> '
            f'{hhmmssmmm(segment.end, millisecond_separator=",")}'
        )

        text = ' '.join(word.word for word in segment.words)
        # SubRip has no convention for speakers, so the name goes into the text.
        if segment.speakerId is not None:
            text = f'{labels[segment.speakerId]}: {text}'
        lines.append(text)

        lines.append('')

    return '\n'.join(lines).encode()
