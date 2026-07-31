"""Fixtures shared by the export tests.

The transcript below is the input of every exporter test. It is deliberately
small but covers the cases every format has to decide about: two speakers, one
of them with an empty name, three segments, one of them without a speaker, and
a text containing characters that need escaping in a markup format.
"""

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.mmt_schema import Transcript

EXPORT_CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'language': 'de',
    'speakers': [
        {'id': 's1', 'name': 'Alice', 'color': '#5b9bd5'},
        {'id': 's2', 'name': '', 'color': '#70ad47'},
    ],
    'segments': [
        {
            'id': 'seg_1',
            'start': 0.0,
            'end': 4.2,
            'speakerId': 's1',
            'words': [
                {
                    'id': 'wrd_1',
                    'start': 0.0,
                    'end': 0.3,
                    'word': 'Hi,',
                    'score': 1.0,
                    'speakerId': 's1',
                },
                {
                    'id': 'wrd_2',
                    'start': 0.4,
                    'end': 0.8,
                    'word': 'wie',
                    'score': 0.9,
                    'speakerId': 's1',
                },
                {
                    'id': 'wrd_3',
                    'start': 0.9,
                    'end': 4.2,
                    'word': 'geht’s?',
                    'score': 0.8,
                    'speakerId': 's1',
                },
            ],
        },
        {
            'id': 'seg_2',
            'start': 4.2,
            'end': 7.9,
            'speakerId': 's2',
            'words': [
                {
                    'id': 'wrd_4',
                    'start': 4.2,
                    'end': 4.5,
                    'word': 'Und',
                    'score': 1.0,
                    'speakerId': 's2',
                },
                {
                    'id': 'wrd_5',
                    'start': 4.6,
                    'end': 7.9,
                    'word': 'dir?',
                    'score': 0.7,
                    'speakerId': 's2',
                },
            ],
        },
        {
            'id': 'seg_3',
            'start': 7.9,
            'end': 12.3456,
            'speakerId': None,
            'words': [
                {
                    'id': 'wrd_6',
                    'start': 7.9,
                    'end': 8.5,
                    'word': 'Ähm,',
                    'score': 0.6,
                    'speakerId': None,
                },
                {
                    'id': 'wrd_7',
                    'start': 8.6,
                    'end': 12.3456,
                    'word': '<gut>',
                    'score': 0.5,
                    'speakerId': None,
                },
            ],
        },
    ],
}


@pytest.fixture
def export_content():
    """The raw mmt-transcript dict, for tests that need to modify it before
    validating. A copy, so a test's modification does not reach another test."""
    return deepcopy(EXPORT_CONTENT)


@pytest.fixture
def export_transcript(export_content):
    return Transcript.model_validate(export_content)


@pytest.fixture
def export_context(export_transcript):
    return ExportContext(
        transcript=export_transcript,
        label='Interview mit Alice',
        created_at=datetime(2026, 7, 30, 9, 15, tzinfo=timezone.utc),
        project_title='Test project',
        filename='interview.wav',
        media_type='audio/wav',
        duration=3600,
    )
