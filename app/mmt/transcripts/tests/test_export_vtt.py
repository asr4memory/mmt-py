"""Tests for the WebVTT exporter.

One segment becomes one cue, however long it is, and its text is emitted on one
line. Splitting a long segment into readable cues is deliberately not part of
this format; see the spec's non-goals.
"""

from dataclasses import replace

import pytest

from mmt.transcripts.exporters import vtt
from mmt.transcripts.mmt_schema import Transcript


@pytest.fixture
def exported(export_context):
    return vtt.export(export_context).decode()


def test_returns_utf8_bytes(export_context):
    result = vtt.export(export_context)

    assert isinstance(result, bytes)
    assert 'Ähm,'.encode() in result


def test_starts_with_the_webvtt_header_and_a_blank_line(exported):
    assert exported.startswith('WEBVTT\n\n')


def test_one_cue_per_segment(exported):
    assert exported.count(' --> ') == 3


def test_timecodes_use_a_dot_before_the_milliseconds(exported):
    assert '00:00:00.000 --> 00:00:04.200' in exported
    assert '00:00:04.200 --> 00:00:07.900' in exported


def test_timecodes_truncate_the_milliseconds(exported):
    assert '00:00:07.900 --> 00:00:12.345' in exported


def test_cue_text_follows_the_timing_line_on_one_line(exported):
    assert '00:00:00.000 --> 00:00:04.200\n<v Alice>Hi, wie geht’s?\n' in exported


def test_voice_tag_carries_the_speakers_name(exported):
    assert '<v Alice>' in exported


def test_voice_tag_falls_back_to_the_speaker_id_when_the_name_is_empty(exported):
    assert '<v s2>Und dir?' in exported


def test_no_voice_tag_for_a_segment_without_a_speaker(exported):
    assert '00:00:07.900 --> 00:00:12.345\nÄhm, &lt;gut&gt;' in exported


def test_cues_are_not_numbered(exported):
    assert '\n1\n' not in exported


def test_exactly_one_blank_line_between_cues(exported):
    assert '\n\n\n' not in exported
    assert exported.count('\n\n') == 3


def test_the_file_ends_with_a_single_newline(exported):
    assert exported.endswith('&lt;gut&gt;\n')


def test_cue_text_escapes_the_three_markup_characters(export_context, export_content):
    export_content['segments'][2]['words'][1]['word'] = '<gut> & so'
    with_markup = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    exported = vtt.export(with_markup).decode()

    assert 'Ähm, &lt;gut&gt; &amp; so' in exported


def test_speaker_name_escapes_the_three_markup_characters(
    export_context, export_content
):
    export_content['speakers'][0]['name'] = 'Alice & <Bob>'
    with_markup = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    exported = vtt.export(with_markup).decode()

    assert '<v Alice &amp; &lt;Bob&gt;>' in exported


def test_escaping_does_not_escape_its_own_escapes(export_context, export_content):
    """The ampersand has to be replaced before the angle brackets, or `<`
    becomes `&amp;lt;`."""
    export_content['segments'][2]['words'][1]['word'] = '<gut>'
    with_markup = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    exported = vtt.export(with_markup).decode()

    assert '&amp;lt;' not in exported
