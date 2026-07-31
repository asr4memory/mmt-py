"""Tests for the CSV exporter.

The file is meant to be opened in a spreadsheet, which is why it is encoded
with a byte order mark and why the times are seconds rather than timecodes.
"""

import csv
import io
from dataclasses import replace

import pytest

from mmt.transcripts.exporters import csv_export
from mmt.transcripts.mmt_schema import Transcript

BOM = '﻿'.encode()


@pytest.fixture
def exported(export_context):
    return csv_export.export(export_context)


@pytest.fixture
def rows(exported):
    text = exported.decode('utf-8-sig')
    return list(csv.reader(io.StringIO(text, newline='')))


def test_returns_bytes(exported):
    assert isinstance(exported, bytes)


def test_the_file_starts_with_a_byte_order_mark(exported):
    """Excel reads a UTF-8 CSV without one as the system's legacy encoding."""
    assert exported.startswith(BOM)


def test_umlauts_are_encoded_as_utf8(exported):
    assert 'Ähm,'.encode() in exported


def test_lines_end_with_carriage_return_and_newline(exported):
    assert exported.endswith(b'\r\n')
    assert b'\n' not in exported.replace(b'\r\n', b'')


def test_the_header_row_names_the_five_columns(rows):
    assert rows[0] == ['index', 'start', 'end', 'speaker', 'text']


def test_one_row_per_segment(rows):
    assert len(rows) == 4


def test_segments_are_numbered_from_one_in_document_order(rows):
    assert [row[0] for row in rows[1:]] == ['1', '2', '3']


def test_times_are_seconds_with_three_decimal_places(rows):
    assert rows[1][1:3] == ['0.000', '4.200']
    assert rows[2][1:3] == ['4.200', '7.900']


def test_times_are_rounded_to_three_decimal_places(rows):
    assert rows[3][2] == '12.346'


def test_the_speaker_cell_holds_the_speaker_name(rows):
    assert rows[1][3] == 'Alice'


def test_the_speaker_cell_falls_back_to_the_speaker_id_for_an_empty_name(rows):
    assert rows[2][3] == 's2'


def test_the_speaker_cell_is_empty_for_a_segment_without_a_speaker(rows):
    assert rows[3][3] == ''


def test_the_text_cell_joins_the_words_with_a_single_space(rows):
    assert rows[1][4] == 'Hi, wie geht’s?'
    assert rows[3][4] == 'Ähm, <gut>'


def test_nothing_is_escaped_in_the_text(rows):
    assert '&lt;' not in rows[3][4]


def test_a_text_containing_a_comma_is_quoted(exported):
    assert b'"Hi, wie geht\xe2\x80\x99s?"' in exported


def test_a_text_containing_a_quotation_mark_is_quoted_and_the_mark_is_doubled(
    export_content, export_context
):
    export_content['segments'][1]['words'][0]['word'] = 'Sie'
    export_content['segments'][1]['words'][1]['word'] = 'sagte "hallo".'
    context = replace_transcript(export_context, export_content)

    exported = csv_export.export(context).decode('utf-8-sig')

    assert '"Sie sagte ""hallo""."' in exported


def test_a_text_containing_a_line_break_is_quoted(export_content, export_context):
    export_content['segments'][1]['words'][0]['word'] = 'Und\ndir?'
    del export_content['segments'][1]['words'][1]
    context = replace_transcript(export_context, export_content)

    exported = csv_export.export(context).decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(exported, newline='')))

    assert rows[2][4] == 'Und\ndir?'


def replace_transcript(context, content):
    """A copy of the context carrying the given content as its transcript."""
    return replace(context, transcript=Transcript.model_validate(content))
