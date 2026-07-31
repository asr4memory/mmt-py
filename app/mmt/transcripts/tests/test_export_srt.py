"""Tests for the SubRip exporter.

SubRip has no convention for speakers, so the speaker's name is written as a
text prefix. SubRip text is plain text, so nothing is escaped.
"""

import pytest

from mmt.transcripts.exporters import srt


@pytest.fixture
def exported(export_context):
    return srt.export(export_context).decode()


def test_returns_utf8_bytes(export_context):
    result = srt.export(export_context)

    assert isinstance(result, bytes)
    assert 'Ähm,'.encode() in result


def test_blocks_are_numbered_from_one_in_document_order(exported):
    assert exported.startswith('1\n')
    assert '\n2\n' in exported
    assert '\n3\n' in exported
    assert '\n4\n' not in exported


def test_timecodes_use_a_comma_before_the_milliseconds(exported):
    assert '00:00:00,000 --> 00:00:04,200' in exported
    assert '00:00:04,200 --> 00:00:07,900' in exported


def test_timecodes_truncate_the_milliseconds(exported):
    assert '00:00:07,900 --> 00:00:12,345' in exported


def test_speaker_name_is_written_as_a_text_prefix(exported):
    assert '00:00:00,000 --> 00:00:04,200\nAlice: Hi, wie geht’s?\n' in exported


def test_speaker_prefix_falls_back_to_the_speaker_id_when_the_name_is_empty(exported):
    assert 's2: Und dir?' in exported


def test_no_prefix_for_a_segment_without_a_speaker(exported):
    assert '00:00:07,900 --> 00:00:12,345\nÄhm, <gut>' in exported


def test_nothing_is_escaped(exported):
    assert '<gut>' in exported
    assert '&lt;' not in exported
    assert '&amp;' not in exported


def test_exactly_one_blank_line_between_blocks(exported):
    assert '\n\n\n' not in exported
    assert exported.count('\n\n') == 2


def test_the_file_ends_with_a_single_newline(exported):
    assert exported.endswith('<gut>\n')
