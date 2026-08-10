from windowing import OVERLAP, WINDOW, merge_windows, windows
from words import entities_to_word_indices, join_words


def test_overlapping_spans_resolved_by_score():
    _, offsets = join_words(["a", "b", "c", "d"])
    entities = [
        {"label": "PER", "start": 0, "end": 5, "score": 0.7},
        {"label": "ORG", "start": 4, "end": 7, "score": 0.9},
    ]
    candidates = entities_to_word_indices(entities, offsets)
    assert merge_windows([((0, 4), candidates)], 4) == [
        {"start": 2, "end": 4, "label": "ORG", "score": 0.9}
    ]


def test_non_overlapping_spans_all_kept_sorted_by_start():
    _, offsets = join_words(["Angela", "Merkel", "besuchte", "Berlin."])
    entities = [
        {"label": "LOC", "start": 23, "end": 29, "score": 0.88},
        {"label": "PER", "start": 0, "end": 13, "score": 0.93},
    ]
    candidates = entities_to_word_indices(entities, offsets)
    assert merge_windows([((0, 4), candidates)], 4) == [
        {"start": 0, "end": 2, "label": "PER", "score": 0.93},
        {"start": 3, "end": 4, "label": "LOC", "score": 0.88},
    ]


def test_short_batch_is_one_window():
    assert windows(50, window=100, overlap=20) == [(0, 50)]


def test_exact_fit_is_one_window():
    assert windows(100, window=100, overlap=20) == [(0, 100)]


def test_windows_partition_with_overlap():
    assert windows(250, window=100, overlap=20) == [(0, 100), (80, 180), (160, 250)]


def test_consecutive_windows_share_exactly_overlap_words():
    spans = windows(1000, window=100, overlap=20)
    for (_, previous_end), (current_start, _) in zip(spans, spans[1:]):
        assert previous_end - current_start == 20


def test_windows_cover_every_word():
    for count in (1, 99, 100, 101, 199, 250, 1000):
        covered = set()
        for start, end in windows(count, window=100, overlap=20):
            covered.update(range(start, end))
        assert covered == set(range(count))


def test_last_window_is_longer_than_overlap():
    """A final window no longer than the overlap would only re-see words the
    previous window already covered."""
    for count in (101, 150, 181, 999):
        start, end = windows(count, window=100, overlap=20)[-1]
        assert end - start > 20


def test_window_defaults_sane():
    assert 0 < OVERLAP < WINDOW
    assert windows(WINDOW) == [(0, WINDOW)]
    assert len(windows(WINDOW + 1)) == 2


def test_merge_single_window_is_pass_through():
    """A batch that fits one window is not shifted and has no cut edges, so
    merging reduces to claim-set resolution of the candidates."""
    candidates = [
        {"start": 0, "end": 2, "label": "PER", "score": 0.7},
        {"start": 1, "end": 3, "label": "ORG", "score": 0.9},
        {"start": 4, "end": 5, "label": "LOC", "score": 0.9},
    ]
    assert merge_windows([((0, 5), candidates)], 5) == [
        {"start": 1, "end": 3, "label": "ORG", "score": 0.9},
        {"start": 4, "end": 5, "label": "LOC", "score": 0.9},
    ]


def test_merge_shifts_window_local_spans_to_batch_coordinates():
    candidate = {"start": 5, "end": 7, "label": "PER", "score": 0.9}
    assert merge_windows([((80, 180), [candidate])], 200) == [
        {"start": 85, "end": 87, "label": "PER", "score": 0.9}
    ]


def test_merge_discards_span_touching_cut_leading_edge():
    candidate = {"start": 0, "end": 2, "label": "PER", "score": 0.9}
    assert merge_windows([((80, 180), [candidate])], 200) == []


def test_merge_discards_span_touching_cut_trailing_edge():
    candidate = {"start": 98, "end": 100, "label": "PER", "score": 0.9}
    assert merge_windows([((0, 100), [candidate])], 200) == []


def test_merge_keeps_spans_at_batch_boundaries():
    """The first word of the batch and the last word of the batch are real
    text boundaries, not window cuts — spans there are genuine."""
    merged = merge_windows(
        [
            ((0, 100), [{"start": 0, "end": 2, "label": "PER", "score": 0.9}]),
            ((80, 180), [{"start": 96, "end": 100, "label": "LOC", "score": 0.9}]),
        ],
        180,
    )
    assert merged == [
        {"start": 0, "end": 2, "label": "PER", "score": 0.9},
        {"start": 176, "end": 180, "label": "LOC", "score": 0.9},
    ]


def test_merge_collapses_cross_window_duplicate_keeping_higher_score():
    merged = merge_windows(
        [
            ((0, 100), [{"start": 85, "end": 87, "label": "PER", "score": 0.88}]),
            ((80, 180), [{"start": 5, "end": 7, "label": "PER", "score": 0.92}]),
        ],
        200,
    )
    assert merged == [{"start": 85, "end": 87, "label": "PER", "score": 0.92}]


def test_merge_truncated_entity_loses_to_full_neighbor():
    """The cut-edge rule in action: window 1 sees only "Angela" at its cut
    trailing edge and scores it higher than window 2's full "Angela Merkel".
    The truncated candidate must be discarded, not win the claim set."""
    merged = merge_windows(
        [
            ((0, 100), [{"start": 99, "end": 100, "label": "PER", "score": 0.95}]),
            ((80, 180), [{"start": 19, "end": 21, "label": "PER", "score": 0.90}]),
        ],
        180,
    )
    assert merged == [{"start": 99, "end": 101, "label": "PER", "score": 0.90}]
