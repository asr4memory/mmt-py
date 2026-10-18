import json

from mmt.transcripts.exporters import export_to_mmt


def test_the_file_is_the_stored_document(export_transcript):
    result = json.loads(export_to_mmt(export_transcript).decode('utf-8'))

    assert result == export_transcript.model_dump()


def test_redacted_words_are_not_replaced(export_transcript):
    assert b'[redacted]' not in export_to_mmt(export_transcript)


def test_the_file_is_indented_and_not_ascii_escaped(export_transcript):
    result = export_to_mmt(export_transcript).decode('utf-8')

    assert result.startswith('{\n  "format": "mmt-transcript",')
    assert 'schön.' in result
