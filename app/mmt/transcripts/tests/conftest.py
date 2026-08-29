from datetime import datetime, timezone

import pytest

from mmt.transcripts.exporters.context import ExportContext
from mmt.transcripts.normalize import normalize_content

# The shared export fixture, described in
# specs/2026-07-30-transcript-export.md under "Tests". Every fallback an
# exporter has to handle is present exactly once, so a format's test does not
# have to build its own content:
#
#   - segment sg1  speaker s1, whose name is set
#   - segment sg2  speaker s2, whose name is the empty string
#   - segment sg3  no speaker at all
#
# Segment sg2 carries the redaction r1 over two consecutive words, one of which
# is the only word referencing mention m1, which is in turn the only mention
# referencing entity e1. Applying the redaction therefore has to drop r1, m1
# and e1 together. Nothing applies redactions before slice 6; until then the
# marked words are exported like any others.


@pytest.fixture
def export_content():
    """The stored mmt-transcript document, as a dict."""
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'language': 'de',
        'speakers': [
            {'id': 's1', 'name': 'Alice', 'color': '#5b9bd5'},
            {'id': 's2', 'name': '', 'color': '#70ad47'},
        ],
        'entities': {
            'e1': {'name': 'Berlin', 'type': 'LOC', 'aliases': [], 'wikidataId': 'Q64'},
        },
        'mentions': {
            'm1': {'label': 'LOC', 'score': 0.9, 'entityId': 'e1'},
            'm2': {'label': 'PER', 'score': 0.8, 'entityId': None},
        },
        'redactions': {
            'r1': {'reason': 'Wohnort', 'start': None, 'end': None},
        },
        'segments': [
            {
                'id': 'sg1',
                'start': 0.0,
                'end': 4.2,
                'speakerId': 's1',
                'words': [
                    _word('w1', 0.0, 0.3, 'Hi,', speaker='s1'),
                    _word('w2', 0.4, 1.0, 'wie', speaker='s1'),
                    _word('w3', 1.1, 1.6, 'geht', speaker='s1'),
                    _word('w4', 1.7, 2.0, 'es', speaker='s1'),
                    _word('w5', 2.1, 4.2, 'dir?', speaker='s1', mention='m2'),
                ],
            },
            {
                'id': 'sg2',
                'start': 4.2,
                'end': 7.9,
                'speakerId': 's2',
                'words': [
                    _word('w6', 4.2, 4.8, 'Ich', speaker='s2'),
                    _word('w7', 4.9, 5.4, 'wohne', speaker='s2'),
                    # The redacted run: contiguous and inside one segment, as
                    # the schema requires.
                    _word('w8', 5.5, 6.2, 'in', speaker='s2', redaction='r1'),
                    _word(
                        'w9',
                        6.3,
                        7.9,
                        'Berlin.',
                        speaker='s2',
                        mention='m1',
                        redaction='r1',
                    ),
                ],
            },
            {
                'id': 'sg3',
                'start': 8.5,
                'end': 10.0,
                'speakerId': None,
                'words': [
                    _word('w10', 8.5, 9.2, 'Aha,'),
                    _word('w11', 9.3, 10.0, 'gut.'),
                ],
            },
        ],
    }


@pytest.fixture
def export_transcript(export_content):
    """The same document as a validated mmt_schema.Transcript."""
    return normalize_content(export_content)


@pytest.fixture
def export_context(export_transcript):
    """The input every exporter receives."""
    return ExportContext(
        transcript=export_transcript,
        label='Interview mit Alice',
        created_at=datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc),
        project_title='Zeitzeugen',
        filename='interview.wav',
        media_type='audio/wav',
        duration=3600,
    )


def _word(word_id, start, end, word, *, speaker=None, mention=None, redaction=None):
    return {
        'id': word_id,
        'start': start,
        'end': end,
        'word': word,
        'score': 1.0,
        'speakerId': speaker,
        'mentionId': mention,
        'redactionId': redaction,
    }
