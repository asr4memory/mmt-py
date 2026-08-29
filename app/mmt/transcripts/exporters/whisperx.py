"""Export as whisperX JSON: the one format carrying word-level timings."""

import json

from mmt.transcripts.mmt_schema import Segment, Transcript, Word

from .context import ExportContext


def export(context: ExportContext) -> bytes:
    transcript = context.transcript
    speaker_labels = _speaker_labels(transcript)

    segments = [
        _segment(segment, speaker_labels) for segment in transcript.segments
    ]
    document = {'segments': segments}

    # whisperX emits every word a second time as a flat list, and downstream
    # tools read it, so it is reproduced rather than left out.
    document['word_segments'] = [
        word for segment in segments for word in segment['words']
    ]

    if transcript.language is not None:
        # Consumers of whisperX output expect a string here, so an unknown
        # language is an absent key rather than a null.
        document = {'language': transcript.language, **document}

    return json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8')


def _segment(segment: Segment, speaker_labels: dict[str, str]) -> dict:
    result = {
        'start': segment.start,
        'end': segment.end,
        # A segment has no stored text: it is its words joined with a single
        # space. whisperX word tokens carry their trailing punctuation, so a
        # plain join reproduces the original spacing.
        'text': ' '.join(word.word for word in segment.words),
    }

    if segment.speakerId is not None:
        result['speaker'] = speaker_labels[segment.speakerId]

    result['words'] = [_word(word, speaker_labels) for word in segment.words]
    return result


def _word(word: Word, speaker_labels: dict[str, str]) -> dict:
    result = {
        'word': word.word,
        'start': word.start,
        'end': word.end,
        'score': word.score,
    }

    if word.speakerId is not None:
        result['speaker'] = speaker_labels[word.speakerId]

    return result


def _speaker_labels(transcript: Transcript) -> dict[str, str]:
    """Map each speaker id to the label whisperX writes for it.

    whisperX's `speaker` field is a label, not a reference, so the mmt speaker
    id is not exported. A speaker whose name is empty has nothing else to be
    called, so its id serves as the label.
    """
    return {
        speaker.id: speaker.name or speaker.id for speaker in transcript.speakers
    }
