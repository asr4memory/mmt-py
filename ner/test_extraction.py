from unittest.mock import Mock, patch

import pytest

from extraction import DEFAULT_THRESHOLD, extract
from windowing import OVERLAP, WINDOW


@pytest.fixture
def mock_model():
    """extract() must not load GLiNER in tests; patch the model behind it."""
    fake_model = Mock()
    fake_model.extract.return_value = _gliner_result({})
    with patch("extraction.get_model", return_value=(fake_model, "fake-schema")):
        yield fake_model


def _gliner_result(entities_by_label):
    return {"entities": entities_by_label}


def test_extract_maps_char_spans_to_word_index_spans(mock_model):
    mock_model.extract.return_value = _gliner_result(
        {
            "PER": [
                {"text": "Angela Merkel", "start": 0, "end": 13, "confidence": 0.93}
            ],
            "LOC": [{"text": "Berlin", "start": 23, "end": 29, "confidence": 0.88}],
        }
    )
    assert extract([["Angela", "Merkel", "besuchte", "Berlin."]]) == [
        [
            {"start": 0, "end": 2, "label": "PER", "score": 0.93},
            {"start": 3, "end": 4, "label": "LOC", "score": 0.88},
        ]
    ]


def test_extract_joins_words_and_requests_spans_with_confidence(mock_model):
    extract([["Angela", "Merkel"]])
    mock_model.extract.assert_called_once_with(
        "Angela Merkel",
        "fake-schema",
        threshold=DEFAULT_THRESHOLD,
        include_spans=True,
        include_confidence=True,
    )


def test_extract_passes_threshold_to_model(mock_model):
    extract([["Angela", "Merkel"]], threshold=0.5)
    assert mock_model.extract.call_args.kwargs["threshold"] == 0.5


def test_extract_results_parallel_to_batches(mock_model):
    mock_model.extract.side_effect = [
        _gliner_result({}),
        _gliner_result(
            {"DATE": [{"text": "2019", "start": 8, "end": 12, "confidence": 0.91}]}
        ),
    ]
    assert extract([["kein", "Treffer"], ["Das", "war", "2019."]]) == [
        [],
        [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}],
    ]


def test_extract_repeated_word_tags_correct_occurrence(mock_model):
    """Regression: the old string re-matching in /enrich tagged the first
    occurrence of a repeated word; char offsets must hit the right one."""
    mock_model.extract.return_value = _gliner_result(
        {"LOC": [{"text": "Berlin", "start": 11, "end": 17, "confidence": 0.9}]}
    )
    assert extract([["Berlin", "ist", "Berlin"]]) == [
        [{"start": 2, "end": 3, "label": "LOC", "score": 0.9}]
    ]


def test_extract_overlapping_spans_resolved_by_score(mock_model):
    mock_model.extract.return_value = _gliner_result(
        {
            "PER": [{"text": "a b", "start": 0, "end": 3, "confidence": 0.7}],
            "ORG": [{"text": "b c", "start": 2, "end": 5, "confidence": 0.9}],
        }
    )
    assert extract([["a", "b", "c"]]) == [
        [{"start": 1, "end": 3, "label": "ORG", "score": 0.9}]
    ]


def test_extract_empty_batch_skips_model_and_returns_empty(mock_model):
    assert extract([[]]) == [[]]
    mock_model.extract.assert_not_called()


def test_extract_no_batches(mock_model):
    assert extract([]) == []


def test_extract_windows_long_batches_and_merges(mock_model):
    """Orchestration across windows: one model call per window on that
    window's joined slice; window-local spans shifted and merged. The window
    partition itself is windowing.py's concern — patched here."""
    mock_model.extract.side_effect = [
        _gliner_result(
            {"PER": [{"text": "a b", "start": 0, "end": 3, "confidence": 0.9}]}
        ),
        _gliner_result(
            {"LOC": [{"text": "e", "start": 4, "end": 5, "confidence": 0.8}]}
        ),
    ]
    with patch("extraction.windows", return_value=[(0, 3), (2, 5)]):
        results = extract([["a", "b", "c", "d", "e"]])
    texts = [call.args[0] for call in mock_model.extract.call_args_list]
    assert texts == ["a b c", "c d e"]
    assert results == [
        [
            {"start": 0, "end": 2, "label": "PER", "score": 0.9},
            {"start": 4, "end": 5, "label": "LOC", "score": 0.8},
        ]
    ]


def test_extract_defaults_to_the_tuned_window_and_overlap(mock_model):
    with patch("extraction.windows", return_value=[(0, 2)]) as windows:
        extract([["Angela", "Merkel"]])
    windows.assert_called_once_with(2, WINDOW, OVERLAP)


def test_extract_passes_window_and_overlap(mock_model):
    with patch("extraction.windows", return_value=[(0, 2)]) as windows:
        extract([["Angela", "Merkel"]], window=3, overlap=1)
    windows.assert_called_once_with(2, 3, 1)


def test_extract_window_none_sends_the_whole_batch_as_one_string(mock_model):
    """Windowing switched off: the batch is not split, however long it is."""
    with patch("extraction.windows") as windows:
        extract([["a", "b", "c"]], window=None)
    windows.assert_not_called()
    assert mock_model.extract.call_args.args[0] == "a b c"
