from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api import app
from extract import enrich_transcript

client = TestClient(app)


def _word(id, word, start, end):
    return {
        "id": id,
        "word": word,
        "start": start,
        "end": end,
        "score": 1.0,
        "speakerId": "spk_1",
        "mentionId": None,
    }


MMT_TRANSCRIPT = {
    "format": "mmt-transcript",
    "version": 1,
    "speakers": [{"id": "spk_1", "name": "Reporter", "color": "#5b9bd5"}],
    "segments": [
        {
            "id": "seg_1",
            "start": 0.0,
            "end": 2.5,
            "text": "Angela Merkel visited Berlin.",
            "speakerId": "spk_1",
            "words": [
                _word("wrd_1", "Angela", 0.0, 0.5),
                _word("wrd_2", "Merkel", 0.6, 1.0),
                _word("wrd_3", "visited", 1.1, 1.6),
                _word("wrd_4", "Berlin.", 1.7, 2.5),
            ],
        }
    ],
}


@pytest.fixture
def mock_enrich():
    """Echo the transcript back so the test exercises (de)serialization only."""
    with patch("api.enrich_transcript", side_effect=lambda t: t) as m:
        yield m


def test_enrich_returns_200(mock_enrich):
    response = client.post("/enrich", json=MMT_TRANSCRIPT)
    assert response.status_code == 200


def test_enrich_preserves_format_version_and_speakers(mock_enrich):
    """Regression: the api models must not strip format/version/speakers."""
    body = client.post("/enrich", json=MMT_TRANSCRIPT).json()
    assert body["format"] == "mmt-transcript"
    assert body["version"] == 1
    assert body["speakers"] == MMT_TRANSCRIPT["speakers"]


def test_enrich_preserves_ids_and_speaker_refs(mock_enrich):
    body = client.post("/enrich", json=MMT_TRANSCRIPT).json()
    segment = body["segments"][0]
    assert segment["id"] == "seg_1"
    assert segment["speakerId"] == "spk_1"
    assert [w["id"] for w in segment["words"]] == ["wrd_1", "wrd_2", "wrd_3", "wrd_4"]
    assert all(w["speakerId"] == "spk_1" for w in segment["words"])


def test_enrich_preserves_unknown_fields(mock_enrich):
    """extra='allow' keeps lenient fields like whisperX score_log."""
    transcript = {
        **MMT_TRANSCRIPT,
        "segments": [
            {
                **MMT_TRANSCRIPT["segments"][0],
                "words": [{**_word("wrd_1", "Angela", 0.0, 0.5), "score_log": -0.01}],
            }
        ],
    }
    body = client.post("/enrich", json=transcript).json()
    assert body["segments"][0]["words"][0]["score_log"] == -0.01


def test_enrich_preserves_mentions_and_mention_refs(mock_enrich):
    """The mirror models the canonical mentions map and per-word
    mentionId, so neither is dropped on the way through."""
    transcript = {
        **MMT_TRANSCRIPT,
        "mentions": {"men_1": {"label": "PER", "score": 1.0}},
        "segments": [
            {
                **MMT_TRANSCRIPT["segments"][0],
                "words": [{**_word("wrd_1", "Angela", 0.0, 0.5), "mentionId": "men_1"}],
            }
        ],
    }
    body = client.post("/enrich", json=transcript).json()
    assert body["mentions"] == {"men_1": {"label": "PER", "score": 1.0}}
    assert body["segments"][0]["words"][0]["mentionId"] == "men_1"


def test_enrich_calls_enrich_transcript(mock_enrich):
    client.post("/enrich", json=MMT_TRANSCRIPT)
    mock_enrich.assert_called_once()
    call_arg = mock_enrich.call_args[0][0]
    assert call_arg["segments"][0]["text"] == "Angela Merkel visited Berlin."


def test_enrich_rejects_non_mmt_input_returns_422():
    """Whisper-shaped input (no format/version/ids) is no longer valid mmt."""
    response = client.post(
        "/enrich",
        json={"segments": [{"start": 0.0, "end": 1.0, "text": "x", "words": []}]},
    )
    assert response.status_code == 422


def test_enrich_missing_segments_returns_422():
    response = client.post("/enrich", json={"foo": "bar"})
    assert response.status_code == 422


def test_extract_tags_freshly_normalized_words():
    """Normalized mmt words are born with ``mentionId: None`` and no
    ``ner_entity`` key. extract.py must still tag matched words with the flat
    ner_entity signal that the app materialises into mentions."""
    fake_model = Mock()
    fake_model.extract.return_value = {"entities": {"PER": ["Angela"]}}

    transcript = {
        "segments": [
            {
                "text": "Angela visited Berlin.",
                "start": 0.0,
                "end": 2.5,
                "words": [
                    {"word": "Angela", "start": 0.0, "end": 0.5, "mentionId": None},
                    {"word": "visited", "start": 0.6, "end": 1.0, "mentionId": None},
                ],
            }
        ]
    }

    with patch("extract.get_model", return_value=(fake_model, None)):
        result = enrich_transcript(transcript)

    assert result["segments"][0]["words"][0]["ner_entity"] == "PER"
    assert result["segments"][0]["words"][1].get("ner_entity") is None
