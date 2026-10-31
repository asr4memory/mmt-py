from unittest import mock

import pytest
import requests

from mmt.transcripts.asr import AsrInfo, AsrModel, asr_info

INFO_BODY = {
    'version': '0.5.0',
    'diarization': True,
    'default_model': 'large-v3',
    'models': [
        {'name': 'large-v3', 'description': 'Whisper large-v3'},
        {'name': 'small', 'description': ''},
    ],
}


def response(status_code=200, json_data=None):
    result = mock.Mock(status_code=status_code)
    result.json.return_value = json_data
    result.raise_for_status.side_effect = (
        requests.HTTPError(f'{status_code} error') if status_code >= 400 else None
    )
    return result


def test_asr_info_returns_the_parsed_information(settings):
    settings.MMT_ASR_API_URL = 'http://asr:8000'

    with mock.patch(
        'mmt.transcripts.asr.requests.get', return_value=response(json_data=INFO_BODY)
    ) as get:
        info = asr_info()

    get.assert_called_once_with('http://asr:8000/info', timeout=2)
    assert info == AsrInfo(
        version='0.5.0',
        diarization=True,
        default_model='large-v3',
        models=(
            AsrModel(name='large-v3', description='Whisper large-v3'),
            AsrModel(name='small', description=''),
        ),
    )


@pytest.mark.parametrize(
    'outcome',
    [
        {'side_effect': requests.ConnectionError('refused')},
        {'return_value': response(status_code=500)},
        {'return_value': response(json_data={'version': '0.5.0', 'diarization': True})},
    ],
    # The names pytest shows for the cases, in the order of the list above.
    ids=['connection error', 'server error', 'body without models'],
)
def test_asr_info_returns_none_when_the_service_is_unavailable(outcome):
    with mock.patch('mmt.transcripts.asr.requests.get', **outcome):
        assert asr_info() is None


@pytest.mark.parametrize(
    'outcome',
    [
        {'return_value': response(json_data=INFO_BODY)},
        {'side_effect': requests.ConnectionError('refused')},
    ],
    ids=['available', 'unavailable'],
)
def test_asr_info_caches_the_outcome(outcome):
    with mock.patch('mmt.transcripts.asr.requests.get', **outcome) as get:
        first = asr_info()
        second = asr_info()

    assert get.call_count == 1
    assert second == first
