import json

from mmt.transcripts.exporters import export_to_whisperx


def exported(transcript):
    return json.loads(export_to_whisperx(transcript).decode('utf-8'))


def test_returns_utf8_bytes(export_transcript):
    result = export_to_whisperx(export_transcript)

    assert isinstance(result, bytes)
    # ensure_ascii=False, so an umlaut is a character and not an escape.
    assert 'schön.'.encode('utf-8') in result


def test_segment_text_is_the_words_joined_with_one_space(export_transcript):
    segments = exported(export_transcript)['segments']

    assert segments[0]['text'] == 'Hi, wie geht es dir?'
    assert segments[1]['text'] == 'Ich wohne XXX XXX'
    assert segments[2]['text'] == 'Aha, schön.'


def test_segments_carry_their_times_and_words(export_transcript):
    first = exported(export_transcript)['segments'][0]

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


def test_speaker_is_the_name(export_transcript):
    assert exported(export_transcript)['segments'][0]['speaker'] == 'Alice'


def test_speaker_falls_back_to_the_id_when_the_name_is_empty(export_transcript):
    # Speaker s2 has an empty name, which is legal in the stored format but
    # useless as a label.
    assert exported(export_transcript)['segments'][1]['speaker'] == 's2'


def test_speaker_key_is_omitted_for_a_segment_without_a_speaker(export_transcript):
    speakerless = exported(export_transcript)['segments'][2]

    assert 'speaker' not in speakerless
    assert all('speaker' not in word for word in speakerless['words'])


def test_word_segments_holds_every_word_in_document_order(export_transcript):
    result = exported(export_transcript)

    words = [word['word'] for word in result['word_segments']]
    assert words == [
        'Hi,',
        'wie',
        'geht',
        'es',
        'dir?',
        'Ich',
        'wohne',
        'XXX',
        'XXX',
        'Aha,',
        'schön.',
    ]


def test_word_segments_entries_have_the_same_shape_as_in_a_segment(export_transcript):
    result = exported(export_transcript)

    assert result['word_segments'][0] == result['segments'][0]['words'][0]
    assert result['word_segments'][-1] == result['segments'][-1]['words'][-1]


def test_language_is_written_when_known(export_transcript):
    assert exported(export_transcript)['language'] == 'de'


def test_language_key_is_omitted_when_unknown(export_transcript):
    # whisperX consumers expect a string in `language`, so an unknown language
    # is an absent key rather than a null.
    export_transcript.language = None

    assert 'language' not in exported(export_transcript)


def test_mmt_identifiers_are_not_exported(export_transcript):
    raw = export_to_whisperx(export_transcript).decode('utf-8')
    result = exported(export_transcript)

    assert 'sg1' not in raw
    assert 'w1' not in raw
    assert all('id' not in segment for segment in result['segments'])
    assert all('id' not in word for word in result['word_segments'])


def test_mentions_and_redactions_are_not_exported(export_transcript):
    raw = export_to_whisperx(export_transcript).decode('utf-8')

    assert 'mentionId' not in raw
    assert 'redactionId' not in raw
    assert 'm1' not in raw
    assert 'r1' not in raw


def test_redacted_words_are_replaced_by_the_marker(export_transcript):
    # Every export applies the transcript's redactions. There is no option to
    # obtain the original words.
    text = exported(export_transcript)['segments'][1]['text']

    assert 'Berlin.' not in text
    assert text == 'Ich wohne XXX XXX'
