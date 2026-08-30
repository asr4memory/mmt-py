"""Resolving speakers to the labels the formats write."""

from mmt.transcripts.mmt_schema import Transcript


def speaker_labels_by_id(transcript: Transcript) -> dict[str, str]:
    """Map each speaker id to the label a format writes for it.

    No format in this set exports the mmt speaker id as a reference; a
    speaker appears as a name. A speaker whose name is empty has nothing else
    to be called, so its id serves as the label.
    """
    return {speaker.id: speaker.name or speaker.id for speaker in transcript.speakers}
