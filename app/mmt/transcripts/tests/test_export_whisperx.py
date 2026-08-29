import json

from mmt.transcripts.exporters import whisperx


def exported(context):
    return json.loads(whisperx.export(context).decode('utf-8'))


def test_returns_utf8_bytes(export_context):
    result = whisperx.export(export_context)

    assert isinstance(result, bytes)
    # ensure_ascii=False, so an umlaut is a character and not an escape.
    assert 'Berlin.'.encode('utf-8') in result


def test_segment_text_is_the_words_joined_with_one_space(export_context):
    segments = exported(export_context)['segments']

    assert segments[0]['text'] == 'Hi, wie geht es dir?'
    assert segments[1]['text'] == 'Ich wohne in Berlin.'
    assert segments[2]['text'] == 'Aha, gut.'


def test_segments_carry_their_times_and_words(export_context):
    first = exported(export_context)['segments'][0]

    assert first['start'] == 0.0
    assert first['end'] == 4.2
    assert [word['word'] for word in first['words']] == [
        'Hi,',
        'wie',
        'geht',
        'es',
        'dir?',
    ]
    assert first['words'][0] == {
        'word': 'Hi,',
        'start': 0.0,
        'end': 0.3,
        'score': 1.0,
        'speaker': 'Alice',
    }


def test_speaker_is_the_name(export_context):
    assert exported(export_context)['segments'][0]['speaker'] == 'Alice'


def test_speaker_falls_back_to_the_id_when_the_name_is_empty(export_context):
    # Speaker s2 has an empty name, which is legal in the stored format but
    # useless as a label.
    assert exported(export_context)['segments'][1]['speaker'] == 's2'


def test_speaker_key_is_omitted_for_a_segment_without_a_speaker(export_context):
    speakerless = exported(export_context)['segments'][2]

    assert 'speaker' not in speakerless
    assert all('speaker' not in word for word in speakerless['words'])


def test_word_segments_holds_every_word_in_document_order(export_context):
    result = exported(export_context)

    words = [word['word'] for word in result['word_segments']]
    assert words == [
        'Hi,',
        'wie',
        'geht',
        'es',
        'dir?',
        'Ich',
        'wohne',
        'in',
        'Berlin.',
        'Aha,',
        'gut.',
    ]


def test_word_segments_entries_have_the_same_shape_as_in_a_segment(export_context):
    result = exported(export_context)

    assert result['word_segments'][0] == result['segments'][0]['words'][0]
    assert result['word_segments'][-1] == result['segments'][-1]['words'][-1]


def test_language_is_written_when_known(export_context):
    assert exported(export_context)['language'] == 'de'


def test_language_key_is_omitted_when_unknown(export_context):
    # whisperX consumers expect a string in `language`, so an unknown language
    # is an absent key rather than a null.
    export_context.transcript.language = None

    assert 'language' not in exported(export_context)


def test_mmt_identifiers_are_not_exported(export_context):
    raw = whisperx.export(export_context).decode('utf-8')
    result = exported(export_context)

    assert 'sg1' not in raw
    assert 'w1' not in raw
    assert all('id' not in segment for segment in result['segments'])
    assert all('id' not in word for word in result['word_segments'])


def test_mentions_and_redactions_are_not_exported(export_context):
    raw = whisperx.export(export_context).decode('utf-8')

    assert 'mentionId' not in raw
    assert 'redactionId' not in raw
    assert 'm1' not in raw
    assert 'r1' not in raw


def test_the_redacted_words_are_exported_verbatim(export_context):
    # Nothing applies redactions yet. The words carrying r1 are written like
    # any others; slice 6 adds the option that replaces them.
    assert 'in Berlin.' in exported(export_context)['segments'][1]['text']
