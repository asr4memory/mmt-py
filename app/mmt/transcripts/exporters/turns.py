"""Group a transcript's segments into speaker turns.

A speaker turn is a run of consecutive segments with the same ``speakerId``.
``speaker_turn_batches`` in ``mmt/transcripts/normalize.py`` groups by the same
rule, but it works on raw dicts and returns flat word dicts for the NER
request, so it cannot be reused here.
"""

from dataclasses import dataclass

from mmt.transcripts.mmt_schema import Segment, Speaker, Transcript


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: Speaker | None
    text: str


def speaker_turns(transcript: Transcript) -> list[SpeakerTurn]:
    """The transcript's segments grouped into turns, in document order.

    ``None`` is a speaker value like any other, so consecutive segments without
    a speaker form one turn and a transcript without any speaker is one single
    turn.
    """
    speakers = {speaker.id: speaker for speaker in transcript.speakers}

    groups: list[list[Segment]] = []
    # A sentinel object rather than None, because None is a speakerId value and
    # the first segment has to start a group in either case.
    previous_speaker_id = object()
    for segment in transcript.segments:
        if segment.speakerId != previous_speaker_id:
            previous_speaker_id = segment.speakerId
            groups.append([])
        groups[-1].append(segment)

    turns = []
    for group in groups:
        speaker_id = group[0].speakerId
        turns.append(
            SpeakerTurn(
                start=group[0].start,
                end=group[-1].end,
                speaker=None if speaker_id is None else speakers[speaker_id],
                text=' '.join(_segment_text(segment) for segment in group),
            )
        )
    return turns


def _segment_text(segment: Segment) -> str:
    return ' '.join(word.word for word in segment.words)
