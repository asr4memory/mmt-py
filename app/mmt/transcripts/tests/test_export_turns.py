import pytest

from mmt.transcripts.exporters.turns import speaker_turns
from mmt.transcripts.mmt_schema import validate_mmt_content


@pytest.fixture
def one_speaker_twice(export_content):
    """sg1 and sg2 both spoken by s1, sg3 without a speaker."""
    segment = export_content['segments'][1]
    segment['speakerId'] = 's1'
    for word in segment['words']:
        word['speakerId'] = 's1'
    return validate_mmt_content(export_content)


def test_consecutive_segments_of_one_speaker_are_one_turn(one_speaker_twice):
    turns = speaker_turns(one_speaker_twice)

    assert [(turn.start, turn.end, turn.text) for turn in turns] == [
        (0.0, 7.9, 'Hi, wie geht es dir? Ich wohne [redacted]'),
        (8.5, 10.0, 'Aha, schön.'),
    ]


def test_a_turn_carries_its_speaker(one_speaker_twice):
    first, second = speaker_turns(one_speaker_twice)

    assert first.speaker.name == 'Alice'
    assert second.speaker is None


def test_a_change_of_speaker_starts_a_new_turn(export_transcript):
    turns = speaker_turns(export_transcript)

    assert [turn.speaker.id if turn.speaker else None for turn in turns] == [
        's1',
        's2',
        None,
    ]
