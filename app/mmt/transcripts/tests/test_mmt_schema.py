import pytest
from django.core.exceptions import ValidationError

from mmt.transcripts.mmt_schema import validate_mmt_content


def valid_content():
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [{'id': 'spk_1', 'name': 'Alice', 'color': '#5b9bd5'}],
        'segments': [
            {
                'id': 'seg_1',
                'start': 0.0,
                'end': 4.2,
                'text': 'Hi',
                'speakerId': 'spk_1',
                'words': [
                    {
                        'id': 'wrd_1',
                        'start': 0.0,
                        'end': 0.3,
                        'word': 'Hi',
                        'score': 1.0,
                        'speakerId': 'spk_1',
                    }
                ],
            }
        ],
    }


def test_accepts_valid():
    validate_mmt_content(valid_content())  # does not raise


def test_accepts_null_speaker_refs():
    content = valid_content()
    content['speakers'] = []
    content['segments'][0]['speakerId'] = None
    content['segments'][0]['words'][0]['speakerId'] = None
    validate_mmt_content(content)  # does not raise


def test_accepts_optional_word_fields():
    content = valid_content()
    word = content['segments'][0]['words'][0]
    word['ner_entity'] = 'PER'
    word['word_group_index'] = 0
    validate_mmt_content(content)  # does not raise


def test_rejects_non_int_word_group_index():
    content = valid_content()
    content['segments'][0]['words'][0]['word_group_index'] = 'first'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_non_dict():
    with pytest.raises(ValidationError):
        validate_mmt_content([])


def test_rejects_wrong_format():
    content = valid_content()
    content['format'] = 'whisper'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_wrong_version():
    content = valid_content()
    content['version'] = 2
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_unknown_key():
    content = valid_content()
    content['segments'][0]['foo'] = 1
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_empty_segments():
    content = valid_content()
    content['segments'] = []
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_empty_words():
    content = valid_content()
    content['segments'][0]['words'] = []
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_bad_color():
    content = valid_content()
    content['speakers'][0]['color'] = 'blue'
    with pytest.raises(ValidationError):
        validate_mmt_content(content)


def test_rejects_dangling_segment_speaker_id():
    content = valid_content()
    content['segments'][0]['speakerId'] = 'spk_ghost'
    with pytest.raises(ValidationError, match='unknown speakerId'):
        validate_mmt_content(content)


def test_rejects_dangling_word_speaker_id():
    content = valid_content()
    content['segments'][0]['words'][0]['speakerId'] = 'spk_ghost'
    with pytest.raises(ValidationError, match='unknown speakerId'):
        validate_mmt_content(content)


def test_rejects_duplicate_speaker_id():
    content = valid_content()
    content['speakers'].append({'id': 'spk_1', 'name': 'Bob', 'color': '#70ad47'})
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_duplicate_word_id_across_segments():
    content = valid_content()
    second = {
        'id': 'seg_2',
        'start': 5.0,
        'end': 6.0,
        'text': 'Hi',
        'speakerId': 'spk_1',
        'words': [
            {
                'id': 'wrd_1',  # duplicate of the first segment's word id
                'start': 5.0,
                'end': 5.3,
                'word': 'Hi',
                'score': 1.0,
                'speakerId': 'spk_1',
            }
        ],
    }
    content['segments'].append(second)
    with pytest.raises(ValidationError, match='duplicate id'):
        validate_mmt_content(content)


def test_rejects_segment_start_after_end():
    content = valid_content()
    content['segments'][0]['start'] = 9.0
    with pytest.raises(ValidationError, match='start after end'):
        validate_mmt_content(content)


def test_rejects_word_start_after_end():
    content = valid_content()
    content['segments'][0]['words'][0]['start'] = 9.0
    with pytest.raises(ValidationError, match='start after end'):
        validate_mmt_content(content)
