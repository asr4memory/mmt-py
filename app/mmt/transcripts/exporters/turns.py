"""Grouping segments into speaker turns, for the formats meant for reading."""

from dataclasses import dataclass

from mmt.transcripts.exporters.words import segment_text
from mmt.transcripts.mmt_schema import Speaker, Transcript


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: Speaker | None
    text: str


def speaker_turns(transcript: Transcript) -> list[SpeakerTurn]:
    """Join consecutive segments with the same speakerId into one turn.

    None is a speakerId like any other, so consecutive segments without a
    speaker are also one turn.
    """
    speakers_by_id = {speaker.id: speaker for speaker in transcript.speakers}

    runs = []
    for segment in transcript.segments:
        if runs and runs[-1][-1].speakerId == segment.speakerId:
            runs[-1].append(segment)
        else:
            runs.append([segment])

    return [
        SpeakerTurn(
            start=run[0].start,
            end=run[-1].end,
            speaker=speakers_by_id.get(run[0].speakerId),
            text=' '.join(
                segment_text(segment, merge_redactions=True) for segment in run
            ),
        )
        for run in runs
    ]
