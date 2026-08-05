import pytest

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.normalize import (
    apply_mention_spans,
    segment_batches,
    speaker_turn_batches,
)


def content_with_words(words, *, segments=None, speaker_ids=None):
    """An mmt-transcript whose single segment holds the given words, or the
    given list of word-lists as separate segments. ``speaker_ids`` assigns
    one speakerId per segment (default: all None); the speakers list is
    derived from the distinct non-null ids."""
    word_lists = segments if segments is not None else [words]
    speaker_ids = speaker_ids or [None] * len(word_lists)
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [
            {'id': speaker_id, 'name': speaker_id, 'color': '#5b9bd5'}
            for speaker_id in sorted({s for s in speaker_ids if s})
        ],
        'entities': {},
        'mentions': {},
        'segments': [
            {
                'id': f'seg_{i}',
                'start': 0.0,
                'end': 1.0,
                'speakerId': speaker_id,
                'words': word_list,
            }
            for i, (word_list, speaker_id) in enumerate(
                zip(word_lists, speaker_ids, strict=True)
            )
        ],
    }


def word(id, **extra):
    return {'id': id, 'word': 'x', 'start': 0.0, 'end': 0.5, 'score': 1.0, **extra}


def span(start, end, label, score=0.9):
    return {'start': start, 'end': end, 'label': label, 'score': score}


def apply(content, results, batcher=speaker_turn_batches):
    """Merge with the same batch list the request would be built from."""
    return apply_mention_spans(content, results, batcher(content))


def test_single_word_span_becomes_one_mention():
    content = apply(
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
    content = apply(
        content_with_words([word('wrd_1'), word('wrd_2'), word('wrd_3')]),
        [[span(0, 2, 'LOC')]],
    )
    assert len(content['mentions']) == 1
    words = content['segments'][0]['words']
    assert words[0]['mentionId'] == words[1]['mentionId']
    assert words[0]['mentionId'] in content['mentions']
    assert words[2]['mentionId'] is None


def test_same_speaker_segments_form_one_batch():
    """Consecutive same-speaker segments are one speaker turn: span indices
    run across the segment boundary, and a boundary-crossing span yields a
    single cross-segment mention (schema-legal: mentions are
    transcript-level)."""
    content = apply(
        content_with_words(
            None,
            segments=[
                [word('wrd_1'), word('wrd_2')],
                [word('wrd_3'), word('wrd_4')],
            ],
        ),
        [[span(1, 3, 'PER', 0.9)]],
    )
    assert len(content['mentions']) == 1
    [mention_id] = content['mentions']
    assert content['segments'][0]['words'][1]['mentionId'] == mention_id
    assert content['segments'][1]['words'][0]['mentionId'] == mention_id
    assert content['segments'][0]['words'][0]['mentionId'] is None
    assert content['segments'][1]['words'][1]['mentionId'] is None
    validate_mmt_content(content)  # does not raise


def test_speaker_change_starts_a_new_batch():
    content = apply(
        content_with_words(
            None,
            segments=[
                [word('wrd_1'), word('wrd_2')],
                [word('wrd_3'), word('wrd_4')],
            ],
            speaker_ids=['spk_a', 'spk_b'],
        ),
        [[span(0, 2, 'ORG')], [span(0, 2, 'PER')]],
    )
    assert len(content['mentions']) == 2
    first = content['segments'][0]['words'][0]['mentionId']
    second = content['segments'][1]['words'][0]['mentionId']
    assert first != second
    validate_mmt_content(content)  # does not raise


def test_non_consecutive_same_speaker_does_not_merge():
    """Turns are runs of *consecutive* equal speakerIds, not groups."""
    content = apply(
        content_with_words(
            None,
            segments=[[word('wrd_1')], [word('wrd_2')], [word('wrd_3')]],
            speaker_ids=['spk_a', 'spk_b', 'spk_a'],
        ),
        [[span(0, 1, 'PER')], [], [span(0, 1, 'LOC')]],
    )
    assert len(content['mentions']) == 2


def test_speakerless_transcript_is_one_whole_transcript_batch():
    """None speakerId is a value like any other: without speakers the whole
    transcript is a single turn (the service windows long batches)."""
    content = apply(
        content_with_words(
            None,
            segments=[[word('wrd_1')], [word('wrd_2')], [word('wrd_3')]],
        ),
        [[span(0, 3, 'ORG', 0.85)]],
    )
    assert len(content['mentions']) == 1
    mention_ids = {segment['words'][0]['mentionId'] for segment in content['segments']}
    assert len(mention_ids) == 1
    validate_mmt_content(content)  # does not raise


def test_segment_batcher_keeps_segments_separate():
    """With segment batches the same-speaker segments that would form one
    turn stay separate batches, and span indices are segment-relative."""
    content = apply(
        content_with_words(
            None,
            segments=[[word('wrd_1'), word('wrd_2')], [word('wrd_3')]],
        ),
        [[span(1, 2, 'PER', 0.9)], [span(0, 1, 'LOC', 0.8)]],
        batcher=segment_batches,
    )
    assert len(content['mentions']) == 2
    assert content['segments'][0]['words'][0]['mentionId'] is None
    per = content['segments'][0]['words'][1]['mentionId']
    loc = content['segments'][1]['words'][0]['mentionId']
    assert content['mentions'][per]['label'] == 'PER'
    assert content['mentions'][loc]['label'] == 'LOC'
    validate_mmt_content(content)  # does not raise


def test_segment_batcher_expects_one_result_list_per_segment():
    # The same two-segment content is ONE turn but TWO segment batches.
    apply(
        content_with_words(None, segments=[[word('wrd_1')], [word('wrd_2')]]),
        [[], []],
        batcher=segment_batches,
    )
    with pytest.raises(ValueError):
        apply(
            content_with_words(None, segments=[[word('wrd_1')], [word('wrd_2')]]),
            [[]],
            batcher=segment_batches,
        )


def test_real_scores_are_stored_per_mention():
    content = apply(
        content_with_words([word('wrd_1'), word('wrd_2')]),
        [[span(0, 1, 'PER', 0.93), span(1, 2, 'LOC', 0.71)]],
    )
    assert sorted(m['score'] for m in content['mentions'].values()) == [0.71, 0.93]


def test_result_validates_as_mmt():
    content = apply(
        content_with_words([word('wrd_1'), word('wrd_2')]),
        [[span(0, 2, 'DATE', 0.91)]],
    )
    validate_mmt_content(content)  # does not raise


def test_no_spans_yields_no_mentions():
    content = apply(content_with_words([word('wrd_1'), word('wrd_2')]), [[]])
    assert content['mentions'] == {}
    assert all(w['mentionId'] is None for w in content['segments'][0]['words'])


def test_replaces_preexisting_mentions():
    """Re-enriching starts from a clean slate: stale mentions and stale
    word links must not survive alongside the new spans."""
    content = content_with_words([word('wrd_1', mentionId='men_old'), word('wrd_2')])
    content['mentions'] = {'men_old': {'label': 'PER', 'score': 1.0}}
    content = apply(content, [[span(1, 2, 'LOC', 0.8)]])
    assert 'men_old' not in content['mentions']
    assert len(content['mentions']) == 1
    assert content['segments'][0]['words'][0]['mentionId'] is None


def test_results_turn_count_mismatch_raises():
    # Two same-speaker segments are ONE turn; two result lists is a
    # protocol error.
    with pytest.raises(ValueError):
        apply(
            content_with_words(None, segments=[[word('wrd_1')], [word('wrd_2')]]),
            [[], []],
        )


def test_span_index_out_of_range_raises():
    with pytest.raises(IndexError):
        apply(content_with_words([word('wrd_1')]), [[span(0, 2, 'PER')]])
