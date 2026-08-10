from words import entities_to_word_indices, join_words


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
    entity = {"label": "PER", "start": 0, "end": 13, "score": 0.93}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 0, "end": 2, "label": "PER", "score": 0.93}
    ]


def test_punctuation_attached_to_word_claims_whole_word():
    """The model sees "Berlin." but typically returns the span of "Berlin";
    the partial char overlap must still claim the full word."""
    _, offsets = join_words(["Angela", "Merkel", "besuchte", "Berlin."])
    entity = {"label": "LOC", "start": 23, "end": 29, "score": 0.88}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 3, "end": 4, "label": "LOC", "score": 0.88}
    ]


def test_repeated_word_maps_to_correct_occurrence():
    """Regression: string re-matching tagged the first occurrence; char
    offsets must attribute the entity to the word actually matched."""
    text, offsets = join_words(["Berlin", "ist", "Berlin"])
    assert text == "Berlin ist Berlin"
    entity = {"label": "LOC", "start": 11, "end": 17, "score": 0.9}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 2, "end": 3, "label": "LOC", "score": 0.9}
    ]


def test_mid_word_span_rounds_to_whole_word():
    _, offsets = join_words(["Angela", "Merkel"])
    entity = {"label": "PER", "start": 2, "end": 4, "score": 0.9}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 0, "end": 1, "label": "PER", "score": 0.9}
    ]


def test_mid_word_span_reaching_into_next_word_claims_both():
    _, offsets = join_words(["Angela", "Merkel"])
    entity = {"label": "PER", "start": 4, "end": 9, "score": 0.9}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 0, "end": 2, "label": "PER", "score": 0.9}
    ]


def test_overlapping_entities_yield_overlapping_spans():
    """entities_to_word_indices maps but does not resolve: both spans must
    be returned, in the order of the entities they came from."""
    _, offsets = join_words(["a", "b", "c", "d"])
    entities = [
        {"label": "PER", "start": 0, "end": 5, "score": 0.7},
        {"label": "ORG", "start": 4, "end": 7, "score": 0.9},
    ]
    assert entities_to_word_indices(entities, offsets) == [
        {"start": 0, "end": 3, "label": "PER", "score": 0.7},
        {"start": 2, "end": 4, "label": "ORG", "score": 0.9},
    ]


def test_empty_batch_yields_no_spans():
    entity = {"label": "PER", "start": 0, "end": 3, "score": 0.9}
    assert entities_to_word_indices([entity], []) == []


def test_no_entities_yields_no_spans():
    _, offsets = join_words(["Angela"])
    assert entities_to_word_indices([], offsets) == []


def test_span_at_batch_end():
    _, offsets = join_words(["besuchte", "Berlin."])
    entity = {"label": "LOC", "start": 9, "end": 16, "score": 0.9}
    assert entities_to_word_indices([entity], offsets) == [
        {"start": 1, "end": 2, "label": "LOC", "score": 0.9}
    ]


def test_entity_overlapping_no_word_is_dropped():
    """A span covering only join whitespace claims nothing."""
    _, offsets = join_words(["Angela", "Merkel"])
    entity = {"label": "PER", "start": 6, "end": 7, "score": 0.9}
    assert entities_to_word_indices([entity], offsets) == []
