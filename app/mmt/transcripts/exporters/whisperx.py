"""Export a transcript in the shape whisperX itself produces.

This is the only format carrying word-level timestamps and confidence scores.
It is not a round trip: the mmt identifiers and the speaker colours have no
place in the whisperX shape, so a consumer that needs them reads the stored
mmt-transcript document instead.
"""

import json

from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.mmt_schema import Word


def export(context: ExportContext) -> bytes:
    transcript = context.transcript
    # whisperX's `speaker` field is a label, not a reference, so a speaker
    # without a name is labelled with its mmt id rather than with an empty
    # string.
    labels = {speaker.id: speaker.name or speaker.id for speaker in transcript.speakers}

    segments = []
    word_segments = []
    for segment in transcript.segments:
        words = [_word(word, labels) for word in segment.words]
        word_segments.extend(words)

        exported = {
            'start': segment.start,
            'end': segment.end,
            # whisperX word tokens carry their trailing punctuation, so joining
            # them with a single space reproduces the original spacing.
            'text': ' '.join(word.word for word in segment.words),
        }
        if segment.speakerId is not None:
            exported['speaker'] = labels[segment.speakerId]
        exported['words'] = words
        segments.append(exported)

    document = {}
    # Consumers of whisperX output expect a string here, so an unknown language
    # is left out rather than written as null.
    if transcript.language is not None:
        document['language'] = transcript.language
    document['segments'] = segments
    # whisperX emits every word a second time as one flat list, and downstream
    # tools read it, so it is reproduced rather than left out.
    document['word_segments'] = word_segments

    return json.dumps(document, ensure_ascii=False, indent=2).encode()


def _word(word: Word, labels: dict[str, str]) -> dict:
    exported = {
        'word': word.word,
        'start': word.start,
        'end': word.end,
        'score': word.score,
    }
    if word.speakerId is not None:
        exported['speaker'] = labels[word.speakerId]
    return exported
