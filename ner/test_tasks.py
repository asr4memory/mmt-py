from unittest.mock import Mock, patch

import pytest

from tasks import extract_entities


@pytest.fixture
def mock_model():
    """The task must not load GLiNER in tests; patch the model behind it."""
    fake_model = Mock()
    fake_model.extract.return_value = {"entities": {}}
    with patch("extraction.get_model", return_value=(fake_model, "fake-schema")):
        yield fake_model


def test_extract_entities_returns_one_span_list_per_batch(mock_model):
    results = extract_entities(
        [["Angela", "Merkel", "besuchte", "Berlin."], ["Das", "war", "2019."]]
    )

    assert results == [[], []]

