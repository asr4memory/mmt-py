from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

SAMPLE_TRANSCRIPT = {
    "segments": [
        {
            "text": "Angela Merkel visited Berlin.",
            "start": 0.0,
            "end": 2.5,
            "words": [
                {"word": "Angela", "start": 0.0, "end": 0.5},
                {"word": "Merkel", "start": 0.6, "end": 1.0},
                {"word": "visited", "start": 1.1, "end": 1.6},
                {"word": "Berlin.", "start": 1.7, "end": 2.5},
            ],
        }
    ]
}


@pytest.fixture
def mock_enrich():
    with patch("api.enrich_transcript", return_value=SAMPLE_TRANSCRIPT) as m:
        yield m


def test_enrich_returns_200(mock_enrich):
    response = client.post("/enrich", json=SAMPLE_TRANSCRIPT)
    assert response.status_code == 200


def test_enrich_calls_enrich_transcript(mock_enrich):
    client.post("/enrich", json=SAMPLE_TRANSCRIPT)
    mock_enrich.assert_called_once()
    call_arg = mock_enrich.call_args[0][0]
    assert call_arg["segments"][0]["text"] == SAMPLE_TRANSCRIPT["segments"][0]["text"]


def test_enrich_empty_segments(mock_enrich):
    transcript = {"segments": []}
    mock_enrich.return_value = transcript
    response = client.post("/enrich", json=transcript)
    assert response.status_code == 200


def test_enrich_missing_segments_returns_422():
    response = client.post("/enrich", json={"foo": "bar"})
    assert response.status_code == 422
