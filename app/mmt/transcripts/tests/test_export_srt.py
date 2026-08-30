from mmt.transcripts.exporters import export_to_srt
from mmt.transcripts.mmt_schema import validate_mmt_content


def exported(transcript):
    return export_to_srt(transcript).decode('utf-8')


def test_returns_utf8_bytes(export_transcript):
    result = export_to_srt(export_transcript)

    assert isinstance(result, bytes)
    assert 'schön.'.encode('utf-8') in result


def test_the_file_is_one_numbered_block_per_segment(export_transcript):
    assert exported(export_transcript) == (
        '1\n'
        '00:00:00,000 --> 00:00:04,200\n'
        'Alice: Hi, wie geht es dir?\n'
        '\n'
        '2\n'
        '00:00:04,200 --> 00:00:07,900\n'
        's2: Ich wohne XXX XXX\n'
        '\n'
        '3\n'
        '00:00:08,500 --> 00:00:10,000\n'
        'Aha, schön.\n'
    )


def test_blocks_are_numbered_from_one(export_transcript):
    assert exported(export_transcript).startswith('1\n')


def test_timecodes_separate_the_milliseconds_with_a_comma(export_transcript):
    assert '00:00:04,200 --> 00:00:07,900' in exported(export_transcript)


def test_the_speaker_name_is_a_text_prefix(export_transcript):
    assert 'Alice: Hi, wie geht es dir?' in exported(export_transcript)


def test_the_prefix_falls_back_to_the_speaker_id_for_an_empty_name(export_transcript):
    assert 's2: Ich wohne' in exported(export_transcript)


def test_a_segment_without_a_speaker_has_no_prefix(export_transcript):
    assert '\nAha, schön.\n' in exported(export_transcript)


def test_a_redacted_word_is_the_marker(export_transcript):
    assert 'Ich wohne XXX XXX' in exported(export_transcript)


def test_markup_characters_are_not_escaped(export_content):
    export_content['speakers'][0]['name'] = 'A & B'
    export_content['segments'][0]['words'][0]['word'] = '<Hi>'
    transcript = validate_mmt_content(export_content)

    # SubRip text is plain text, so the transcript's characters are written
    # as they stand.
    assert 'A & B: <Hi> wie geht es dir?' in exported(transcript)
