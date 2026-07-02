from align import (
    OVERLAP,
    WINDOW,
    join_words,
    merge_windows,
    to_word_spans,
    windows,
)


def _entity(label, start, end, score=0.9):
    return {"label": label, "start": start, "end": end, "score": score}


def _span(start, end, label, score=0.9):
    return {"start": start, "end": end, "label": label, "score": score}


def test_join_words_empty():
    assert join_words([]) == ("", [])


def test_join_words_single_word():
    assert join_words(["Berlin."]) == ("Berlin.", [(0, 7)])


def test_join_words_offsets_slice_back_to_words():
    words = ["Angela", "Merkel", "besuchte", "Berlin."]
    text, offsets = join_words(words)
    assert text == "Angela Merkel besuchte Berlin."
    assert offsets == [(0, 6), (7, 13), (14, 22), (23, 30)]
    for (start, end), word in zip(offsets, words):
        assert text[start:end] == word


def test_exact_alignment_multi_word_entity():
    _, offsets = join_words(["Angela", "Merkel", "besuchte", "Berlin."])
    spans = to_word_spans([_entity("PER", 0, 13, 0.93)], offsets)
    assert spans == [_span(0, 2, "PER", 0.93)]


def test_punctuation_attached_to_word_claims_whole_word():
    """The model sees "Berlin." but typically returns the span of "Berlin";
    the partial char overlap must still claim the full word."""
    _, offsets = join_words(["Angela", "Merkel", "besuchte", "Berlin."])
    spans = to_word_spans([_entity("LOC", 23, 29, 0.88)], offsets)
    assert spans == [_span(3, 4, "LOC", 0.88)]


def test_repeated_word_maps_to_correct_occurrence():
    """Regression: string re-matching tagged the first occurrence; char
    offsets must attribute the entity to the word actually matched."""
    text, offsets = join_words(["Berlin", "ist", "Berlin"])
    assert text == "Berlin ist Berlin"
    spans = to_word_spans([_entity("LOC", 11, 17)], offsets)
    assert spans == [_span(2, 3, "LOC")]


def test_mid_word_span_rounds_to_whole_word():
    _, offsets = join_words(["Angela", "Merkel"])
    spans = to_word_spans([_entity("PER", 2, 4)], offsets)
    assert spans == [_span(0, 1, "PER")]


def test_mid_word_span_reaching_into_next_word_claims_both():
    _, offsets = join_words(["Angela", "Merkel"])
    spans = to_word_spans([_entity("PER", 4, 9)], offsets)
    assert spans == [_span(0, 2, "PER")]


def test_overlapping_spans_resolved_by_score():
    _, offsets = join_words(["a", "b", "c", "d"])
    spans = to_word_spans(
        [_entity("PER", 0, 5, score=0.7), _entity("ORG", 4, 7, score=0.9)],
        offsets,
    )
    assert spans == [_span(2, 4, "ORG")]


def test_non_overlapping_spans_all_kept_sorted_by_start():
    _, offsets = join_words(["Angela", "Merkel", "besuchte", "Berlin."])
    spans = to_word_spans(
        [_entity("LOC", 23, 29, 0.88), _entity("PER", 0, 13, 0.93)],
        offsets,
    )
    assert spans == [_span(0, 2, "PER", 0.93), _span(3, 4, "LOC", 0.88)]


def test_empty_batch_yields_no_spans():
    assert to_word_spans([_entity("PER", 0, 3)], []) == []


def test_no_entities_yields_no_spans():
    _, offsets = join_words(["Angela"])
    assert to_word_spans([], offsets) == []


def test_span_at_batch_end():
    _, offsets = join_words(["besuchte", "Berlin."])
    spans = to_word_spans([_entity("LOC", 9, 16)], offsets)
    assert spans == [_span(1, 2, "LOC")]


def test_entity_overlapping_no_word_is_dropped():
    """A span covering only join whitespace claims nothing."""
    _, offsets = join_words(["Angela", "Merkel"])
    assert to_word_spans([_entity("PER", 6, 7)], offsets) == []


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
    """A batch that fits one window must behave exactly like to_word_spans:
    no shifting, no edge discards, same claim-set resolution."""
    candidates = [
        _span(0, 2, "PER", 0.7),
        _span(1, 3, "ORG", 0.9),
        _span(4, 5, "LOC"),
    ]
    assert merge_windows([((0, 5), candidates)], 5) == [
        _span(1, 3, "ORG", 0.9),
        _span(4, 5, "LOC"),
    ]


def test_merge_shifts_window_local_spans_to_batch_coordinates():
    merged = merge_windows([((80, 180), [_span(5, 7, "PER")])], 200)
    assert merged == [_span(85, 87, "PER")]


def test_merge_discards_span_touching_cut_leading_edge():
    assert merge_windows([((80, 180), [_span(0, 2, "PER")])], 200) == []


def test_merge_discards_span_touching_cut_trailing_edge():
    assert merge_windows([((0, 100), [_span(98, 100, "PER")])], 200) == []


def test_merge_keeps_spans_at_batch_boundaries():
    """The first word of the batch and the last word of the batch are real
    text boundaries, not window cuts — spans there are genuine."""
    merged = merge_windows(
        [
            ((0, 100), [_span(0, 2, "PER")]),
            ((80, 180), [_span(96, 100, "LOC")]),
        ],
        180,
    )
    assert merged == [_span(0, 2, "PER"), _span(176, 180, "LOC")]


def test_merge_collapses_cross_window_duplicate_keeping_higher_score():
    merged = merge_windows(
        [
            ((0, 100), [_span(85, 87, "PER", 0.88)]),
            ((80, 180), [_span(5, 7, "PER", 0.92)]),
        ],
        200,
    )
    assert merged == [_span(85, 87, "PER", 0.92)]


def test_merge_truncated_entity_loses_to_full_neighbor():
    """The cut-edge rule in action: window 1 sees only "Angela" at its cut
    trailing edge and scores it higher than window 2's full "Angela Merkel".
    The truncated candidate must be discarded, not win the claim set."""
    merged = merge_windows(
        [
            ((0, 100), [_span(99, 100, "PER", 0.95)]),
            ((80, 180), [_span(19, 21, "PER", 0.90)]),
        ],
        180,
    )
    assert merged == [_span(99, 101, "PER", 0.90)]
