"""Tests for the whisperX JSON exporter.

This is the only format carrying word-level timestamps and confidence scores,
so it is the closest an export gets to the stored content. It is still lossy:
the mmt identifiers and the speaker colours are not part of the whisperX shape.
"""

import json
from dataclasses import replace

import pytest

from mmt.transcripts.exporters import whisperx
from mmt.transcripts.mmt_schema import Transcript


@pytest.fixture
def exported(export_context):
    return json.loads(whisperx.export(export_context))


def test_returns_utf8_bytes_without_escaping_non_ascii(export_context):
    result = whisperx.export(export_context)

    assert isinstance(result, bytes)
    assert 'Ähm,'.encode() in result


def test_language_is_the_content_language(exported):
    assert exported['language'] == 'de'


def test_language_key_is_omitted_when_the_language_is_unknown(
    export_context, export_content
):
    export_content['language'] = None
    without_language = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    exported = json.loads(whisperx.export(without_language))

    assert 'language' not in exported


def test_one_segment_per_stored_segment(exported):
    assert len(exported['segments']) == 3
    assert [segment['start'] for segment in exported['segments']] == [0.0, 4.2, 7.9]
    assert [segment['end'] for segment in exported['segments']] == [4.2, 7.9, 12.3456]


def test_segment_text_joins_the_words_with_a_single_space(exported):
    assert exported['segments'][0]['text'] == 'Hi, wie geht’s?'
    assert exported['segments'][1]['text'] == 'Und dir?'


def test_speaker_is_the_speakers_name(exported):
    assert exported['segments'][0]['speaker'] == 'Alice'


def test_speaker_falls_back_to_the_speaker_id_when_the_name_is_empty(exported):
    assert exported['segments'][1]['speaker'] == 's2'


def test_speaker_key_is_omitted_for_a_segment_without_a_speaker(exported):
    assert 'speaker' not in exported['segments'][2]


def test_words_carry_their_timings_and_score(exported):
    assert exported['segments'][0]['words'][0] == {
        'word': 'Hi,',
        'start': 0.0,
        'end': 0.3,
        'score': 1.0,
        'speaker': 'Alice',
    }


def test_speaker_key_is_omitted_for_a_word_without_a_speaker(exported):
    for word in exported['segments'][2]['words']:
        assert 'speaker' not in word


def test_word_segments_holds_every_word_in_document_order(exported):
    assert [word['word'] for word in exported['word_segments']] == [
        'Hi,',
        'wie',
        'geht’s?',
        'Und',
        'dir?',
        'Ähm,',
        '<gut>',
    ]


def test_word_segments_entries_have_the_same_shape_as_inside_a_segment(exported):
    assert exported['word_segments'][0] == exported['segments'][0]['words'][0]


def test_mmt_ids_are_not_exported(export_context):
    result = whisperx.export(export_context).decode()

    assert 'seg_1' not in result
    assert 'wrd_1' not in result
    for segment in json.loads(result)['segments']:
        assert 'id' not in segment
        for word in segment['words']:
            assert 'id' not in word
            assert 'speakerId' not in word
            assert 'mentionId' not in word
