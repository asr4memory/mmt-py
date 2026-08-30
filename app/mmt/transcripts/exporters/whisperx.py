"""Export as whisperX JSON: the one format carrying word-level timings."""

import json

from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.words import word_text
from mmt.transcripts.mmt_schema import Segment, Transcript, Word


def export_to_whisperx(transcript: Transcript) -> bytes:
    speaker_labels = speaker_labels_by_id(transcript)

    segments = [
        _segment_to_dict(segment, speaker_labels) for segment in transcript.segments
    ]
    # whisperX repeats every word in a flat list, and downstream tools read it.
    word_segments = [word for segment in segments for word in segment['words']]

    # Insertion order is the key order in the file, so these assignments are
    # in the order the keys should appear.
    document = {}
    if transcript.language is not None:
        # An unknown language is an absent key, not a null.
        document['language'] = transcript.language
    document['segments'] = segments
    document['word_segments'] = word_segments

    return json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8')


def _segment_to_dict(segment: Segment, speaker_labels: dict[str, str]) -> dict:
    result = {
        'start': segment.start,
        'end': segment.end,
        # A segment has no stored text: it is its words joined with a single
        # space. whisperX word tokens carry their trailing punctuation, so a
        # plain join reproduces the original spacing.
        'text': ' '.join(word_text(word) for word in segment.words),
    }

    if segment.speakerId is not None:
        result['speaker'] = speaker_labels[segment.speakerId]

    result['words'] = [_word_to_dict(word, speaker_labels) for word in segment.words]
    return result


def _word_to_dict(word: Word, speaker_labels: dict[str, str]) -> dict:
    result = {
        'word': word_text(word),
        'start': word.start,
        'end': word.end,
        'score': word.score,
    }

    if word.speakerId is not None:
        result['speaker'] = speaker_labels[word.speakerId]

    return result
