from align import join_words, to_word_spans


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
