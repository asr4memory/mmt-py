import pytest

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.normalize import apply_mention_spans


def content_with_words(words, *, segments=None):
    """An mmt-transcript whose single segment holds the given words, or the
    given list of word-lists as separate segments."""
    word_lists = segments if segments is not None else [words]
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [],
        'mentions': {},
        'segments': [
            {
                'id': f'seg_{i}',
                'start': 0.0,
                'end': 1.0,
                'text': 'x',
                'speakerId': None,
                'words': word_list,
            }
            for i, word_list in enumerate(word_lists)
        ],
    }


def word(id, **extra):
    return {'id': id, 'word': 'x', 'start': 0.0, 'end': 0.5, 'score': 1.0, **extra}


def span(start, end, label, score=0.9):
    return {'start': start, 'end': end, 'label': label, 'score': score}


def test_single_word_span_becomes_one_mention():
    content = apply_mention_spans(
        content_with_words([word('wrd_1'), word('wrd_2')]),
        [[span(0, 1, 'PER', 0.93)]],
    )
    assert len(content['mentions']) == 1
    [(mention_id, mention)] = content['mentions'].items()
    assert mention == {'label': 'PER', 'score': 0.93}
    words = content['segments'][0]['words']
    assert words[0]['mentionId'] == mention_id
    assert words[1]['mentionId'] is None


def test_multi_word_span_shares_one_mention():
    content = apply_mention_spans(
        content_with_words([word('wrd_1'), word('wrd_2'), word('wrd_3')]),
        [[span(0, 2, 'LOC')]],
    )
    assert len(content['mentions']) == 1
    words = content['segments'][0]['words']
    assert words[0]['mentionId'] == words[1]['mentionId']
    assert words[0]['mentionId'] in content['mentions']
    assert words[2]['mentionId'] is None


def test_spans_in_different_segments_are_distinct_mentions():
    content = apply_mention_spans(
        content_with_words(
            None,
            segments=[
                [word('wrd_1'), word('wrd_2')],
                [word('wrd_3'), word('wrd_4')],
            ],
        ),
        [[span(0, 2, 'ORG')], [span(0, 2, 'PER')]],
    )
    assert len(content['mentions']) == 2
    first = content['segments'][0]['words'][0]['mentionId']
    second = content['segments'][1]['words'][0]['mentionId']
    assert first != second


def test_real_scores_are_stored_per_mention():
    content = apply_mention_spans(
        content_with_words([word('wrd_1'), word('wrd_2')]),
        [[span(0, 1, 'PER', 0.93), span(1, 2, 'LOC', 0.71)]],
    )
    assert sorted(m['score'] for m in content['mentions'].values()) == [0.71, 0.93]


def test_result_validates_as_mmt():
    content = apply_mention_spans(
        content_with_words([word('wrd_1'), word('wrd_2')]),
        [[span(0, 2, 'DATE', 0.91)]],
    )
    validate_mmt_content(content)  # does not raise


def test_no_spans_yields_no_mentions():
    content = apply_mention_spans(
        content_with_words([word('wrd_1'), word('wrd_2')]), [[]]
    )
    assert content['mentions'] == {}
    assert all(w['mentionId'] is None for w in content['segments'][0]['words'])


def test_replaces_preexisting_mentions():
    """Re-enriching starts from a clean slate: stale mentions and stale
    word links must not survive alongside the new spans."""
    content = content_with_words(
        [word('wrd_1', mentionId='men_old'), word('wrd_2')]
    )
    content['mentions'] = {'men_old': {'label': 'PER', 'score': 1.0}}
    content = apply_mention_spans(content, [[span(1, 2, 'LOC', 0.8)]])
    assert 'men_old' not in content['mentions']
    assert len(content['mentions']) == 1
    assert content['segments'][0]['words'][0]['mentionId'] is None


def test_results_segment_count_mismatch_raises():
    with pytest.raises(ValueError):
        apply_mention_spans(content_with_words([word('wrd_1')]), [[], []])


def test_span_index_out_of_range_raises():
    with pytest.raises(IndexError):
        apply_mention_spans(
            content_with_words([word('wrd_1')]), [[span(0, 2, 'PER')]]
        )
