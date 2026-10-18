import csv
import io

from mmt.transcripts.exporters import export_to_csv
from mmt.transcripts.mmt_schema import validate_mmt_content


def rows(transcript):
    text = export_to_csv(transcript).decode('utf-8')
    return list(csv.reader(io.StringIO(text, newline='')))


def test_the_file_is_a_header_and_one_row_per_segment(export_transcript):
    assert rows(export_transcript) == [
        ['index', 'start', 'end', 'speaker', 'text'],
        ['1', '0.000', '4.200', 'Alice', 'Hi, wie geht es dir?'],
        ['2', '4.200', '7.900', 's2', 'Ich wohne [redacted]'],
        ['3', '8.500', '10.000', '', 'Aha, schön.'],
    ]


def test_lines_end_with_crlf(export_transcript):
    assert export_to_csv(export_transcript).startswith(
        b'index,start,end,speaker,text\r\n'
    )


def test_the_file_is_utf8_without_a_byte_order_mark(export_transcript):
    result = export_to_csv(export_transcript)

    assert result.startswith(b'index')
    assert 'schön.'.encode('utf-8') in result


def test_a_text_with_a_comma_and_a_quotation_mark_is_quoted(export_content):
    export_content['segments'][2]['words'][0]['word'] = 'Er sagte "ja",'
    transcript = validate_mmt_content(export_content)

    result = export_to_csv(transcript).decode('utf-8')

    assert '"Er sagte ""ja"", schön."' in result
