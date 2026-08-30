"""Export as WebVTT: one cue per segment, for a video player."""

from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.timecode import hhmmssmmm
from mmt.transcripts.exporters.words import word_text
from mmt.transcripts.mmt_schema import Segment, Transcript


def export_to_vtt(transcript: Transcript) -> bytes:
    speaker_labels = speaker_labels_by_id(transcript)

    cues = [_cue(segment, speaker_labels) for segment in transcript.segments]
    # One blank line after the header and one between cues.
    return ('WEBVTT\n\n' + '\n\n'.join(cues) + '\n').encode('utf-8')


def _cue(segment: Segment, speaker_labels: dict[str, str]) -> str:
    times = f'{hhmmssmmm(segment.start)} --> {hhmmssmmm(segment.end)}'
    # A segment has no stored text: it is its words joined with a single
    # space. The word tokens carry their trailing punctuation, so a plain
    # join reproduces the original spacing.
    text = _escape(' '.join(word_text(word) for word in segment.words))

    if segment.speakerId is not None:
        text = f'<v {_escape(speaker_labels[segment.speakerId])}>{text}'

    # Cues are not numbered: VTT allows an optional identifier line, and no
    # player requires it.
    return f'{times}\n{text}'


def _escape(text: str) -> str:
    """Escape the three characters that are markup in VTT cue text."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
