"""Export as SubRip: one numbered block per segment, for a video player."""

from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.timecode import hhmmssmmm
from mmt.transcripts.exporters.words import word_text
from mmt.transcripts.mmt_schema import Segment, Transcript


def export_to_srt(transcript: Transcript) -> bytes:
    speaker_labels = speaker_labels_by_id(transcript)

    blocks = [
        _block(number, segment, speaker_labels)
        for number, segment in enumerate(transcript.segments, start=1)
    ]
    return ('\n\n'.join(blocks) + '\n').encode('utf-8')


def _block(number: int, segment: Segment, speaker_labels: dict[str, str]) -> str:
    times = (
        f'{hhmmssmmm(segment.start, millisecond_separator=",")} --> '
        f'{hhmmssmmm(segment.end, millisecond_separator=",")}'
    )
    # A segment has no stored text: it is its words joined with a single
    # space. The word tokens carry their trailing punctuation, so a plain
    # join reproduces the original spacing.
    text = ' '.join(word_text(word) for word in segment.words)

    if segment.speakerId is not None:
        # SubRip has no speaker convention, so the name is written as a text
        # prefix. The text itself is not escaped: SubRip text is plain text.
        text = f'{speaker_labels[segment.speakerId]}: {text}'

    return f'{number}\n{times}\n{text}'
