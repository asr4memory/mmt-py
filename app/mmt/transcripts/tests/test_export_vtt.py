import pytest

from mmt.transcripts.exporters import export_to_vtt
from mmt.transcripts.mmt_schema import validate_mmt_content


def exported(transcript):
    return export_to_vtt(transcript).decode('utf-8')


@pytest.fixture
def markup_transcript(export_content):
    """The shared document with markup characters in a speaker name and in a
    word, which VTT has to escape."""
    export_content['speakers'][0]['name'] = 'A & B <boss>'
    export_content['segments'][0]['words'][0]['word'] = '<Hi>'
    export_content['segments'][0]['words'][1]['word'] = '&'
    return validate_mmt_content(export_content)


def test_returns_utf8_bytes(export_transcript):
    result = export_to_vtt(export_transcript)

    assert isinstance(result, bytes)
    assert 'schön.'.encode('utf-8') in result


def test_the_file_is_the_header_and_one_cue_per_segment(export_transcript):
    assert exported(export_transcript) == (
        'WEBVTT\n'
        '\n'
        '00:00:00.000 --> 00:00:04.200\n'
        '<v Alice>Hi, wie geht es dir?\n'
        '\n'
        '00:00:04.200 --> 00:00:07.900\n'
        '<v s2>Ich wohne XXX XXX\n'
        '\n'
        '00:00:08.500 --> 00:00:10.000\n'
        'Aha, schön.\n'
    )


def test_the_file_starts_with_the_webvtt_header_and_a_blank_line(export_transcript):
    assert exported(export_transcript).startswith('WEBVTT\n\n')


def test_timecodes_separate_the_milliseconds_with_a_dot(export_transcript):
    assert '00:00:04.200 --> 00:00:07.900' in exported(export_transcript)


def test_cues_are_not_numbered(export_transcript):
    lines = exported(export_transcript).splitlines()

    assert '1' not in lines


def test_the_voice_tag_carries_the_speaker_name(export_transcript):
    assert '<v Alice>Hi, wie geht es dir?' in exported(export_transcript)


def test_the_voice_tag_falls_back_to_the_speaker_id_for_an_empty_name(
    export_transcript,
):
    # Speaker s2 has an empty name, which is legal in the stored format but
    # useless as a label.
    assert '<v s2>Ich wohne' in exported(export_transcript)


def test_a_segment_without_a_speaker_has_no_voice_tag(export_transcript):
    assert '\nAha, schön.\n' in exported(export_transcript)


def test_a_redacted_word_is_the_marker(export_transcript):
    assert 'Ich wohne XXX XXX' in exported(export_transcript)


def test_markup_characters_in_the_cue_text_are_escaped(markup_transcript):
    assert '&lt;Hi&gt; &amp; geht es dir?' in exported(markup_transcript)


def test_markup_characters_in_the_speaker_name_are_escaped(markup_transcript):
    assert '<v A &amp; B &lt;boss&gt;>' in exported(markup_transcript)
