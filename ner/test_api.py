from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api import VERSION, app

client = TestClient(app)


@pytest.fixture
def mock_model():
    """/extract must not load GLiNER in tests; patch the model behind it."""
    fake_model = Mock()
    with patch("api.get_model", return_value=(fake_model, "fake-schema")):
        yield fake_model


def _gliner_result(entities_by_label):
    return {"entities": entities_by_label}


def test_health_reports_ok_and_version():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION}


def test_health_does_not_load_the_model():
    """The health check must stay cheap: it must not pull GLiNER into memory."""
    with patch("api.get_model") as get_model:
        client.get("/health")
    get_model.assert_not_called()


def test_extract_maps_char_spans_to_word_index_spans(mock_model):
    mock_model.extract.return_value = _gliner_result(
        {
            "PER": [{"text": "Angela Merkel", "start": 0, "end": 13, "confidence": 0.93}],
            "LOC": [{"text": "Berlin", "start": 23, "end": 29, "confidence": 0.88}],
        }
    )
    response = client.post(
        "/extract",
        json={"batches": [["Angela", "Merkel", "besuchte", "Berlin."]]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "results": [
            [
                {"start": 0, "end": 2, "label": "PER", "score": 0.93},
                {"start": 3, "end": 4, "label": "LOC", "score": 0.88},
            ]
        ]
    }


def test_extract_joins_words_and_requests_spans_with_confidence(mock_model):
    mock_model.extract.return_value = _gliner_result({})
    client.post("/extract", json={"batches": [["Angela", "Merkel"]]})
    mock_model.extract.assert_called_once_with(
        "Angela Merkel",
        "fake-schema",
        threshold=0.5,
        include_spans=True,
        include_confidence=True,
    )


def test_extract_results_parallel_to_batches(mock_model):
    mock_model.extract.side_effect = [
        _gliner_result({}),
        _gliner_result(
            {"DATE": [{"text": "2019", "start": 8, "end": 12, "confidence": 0.91}]}
        ),
    ]
    body = client.post(
        "/extract",
        json={"batches": [["kein", "Treffer"], ["Das", "war", "2019."]]},
    ).json()
    assert body["results"] == [
        [],
        [{"start": 2, "end": 3, "label": "DATE", "score": 0.91}],
    ]


def test_extract_repeated_word_tags_correct_occurrence(mock_model):
    """Regression: the old string re-matching in /enrich tagged the first
    occurrence of a repeated word; char offsets must hit the right one."""
    mock_model.extract.return_value = _gliner_result(
        {"LOC": [{"text": "Berlin", "start": 11, "end": 17, "confidence": 0.9}]}
    )
    body = client.post(
        "/extract", json={"batches": [["Berlin", "ist", "Berlin"]]}
    ).json()
    assert body["results"] == [[{"start": 2, "end": 3, "label": "LOC", "score": 0.9}]]


def test_extract_overlapping_spans_resolved_by_score(mock_model):
    mock_model.extract.return_value = _gliner_result(
        {
            "PER": [{"text": "a b", "start": 0, "end": 3, "confidence": 0.7}],
            "ORG": [{"text": "b c", "start": 2, "end": 5, "confidence": 0.9}],
        }
    )
    body = client.post("/extract", json={"batches": [["a", "b", "c"]]}).json()
    assert body["results"] == [[{"start": 1, "end": 3, "label": "ORG", "score": 0.9}]]


def test_extract_empty_batch_skips_model_and_returns_empty(mock_model):
    body = client.post("/extract", json={"batches": [[]]}).json()
    assert body["results"] == [[]]
    mock_model.extract.assert_not_called()


def test_extract_no_batches(mock_model):
    body = client.post("/extract", json={"batches": []}).json()
    assert body["results"] == []


def test_extract_long_batch_is_one_model_call(mock_model):
    """No windowing: a batch is sent to the model as one string, whatever
    its length."""
    mock_model.extract.return_value = _gliner_result({})
    words = [f"w{i}" for i in range(500)]
    client.post("/extract", json={"batches": [words]})
    mock_model.extract.assert_called_once()
    assert mock_model.extract.call_args.args[0] == " ".join(words)


def test_extract_missing_batches_returns_422():
    assert client.post("/extract", json={}).status_code == 422


def test_extract_malformed_batches_returns_422():
    response = client.post("/extract", json={"batches": ["not", "nested"]})
    assert response.status_code == 422
