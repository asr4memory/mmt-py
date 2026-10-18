from mmt.transcripts.exporters.words import segment_text
from mmt.transcripts.mmt_schema import Segment, Word


def _segment(*words):
    return Segment(
        id='sg1',
        start=0.0,
        end=float(len(words)),
        words=[
            Word(id=f'w{i}', start=i, end=i + 1, word=text, score=1.0, redactionId=r)
            for i, (text, r) in enumerate(words)
        ],
    )


def test_words_are_joined_with_one_space():
    segment = _segment(('Hi,', None), ('du.', None))

    assert segment_text(segment, merge_redactions=True) == 'Hi, du.'


def test_a_run_of_one_redaction_is_one_marker_when_merged():
    segment = _segment(('Ich', None), ('in', 'r1'), ('Berlin.', 'r1'), ('ja', None))

    assert segment_text(segment, merge_redactions=True) == 'Ich [redacted] ja'


def test_adjacent_redactions_are_one_marker_each_when_merged():
    segment = _segment(('Anna', 'r1'), ('Berlin', 'r2'))

    assert segment_text(segment, merge_redactions=True) == '[redacted] [redacted]'


def test_every_redacted_word_is_a_marker_when_not_merged():
    segment = _segment(('Ich', None), ('in', 'r1'), ('Berlin.', 'r1'))

    assert segment_text(segment, merge_redactions=False) == (
        'Ich [redacted] [redacted]'
    )
