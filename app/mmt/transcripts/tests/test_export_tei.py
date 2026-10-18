import datetime
import xml.etree.ElementTree as ET

from mmt.transcripts.exporters import export_to_tei
from mmt.transcripts.mmt_schema import validate_mmt_content

TEI = '{http://www.tei-c.org/ns/1.0}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def exported(transcript, **overrides):
    arguments = {
        'title': 'Interview mit Alice',
        'media_filename': 'interview.wav',
        'media_type': 'audio/wav',
        'duration': 3600,
        'export_date': datetime.date(2026, 10, 18),
    } | overrides
    return export_to_tei(transcript, **arguments)


def parsed(transcript, **overrides):
    return ET.fromstring(exported(transcript, **overrides))


def test_the_document_starts_with_an_xml_declaration(export_transcript):
    assert exported(export_transcript).startswith(
        b"<?xml version='1.0' encoding='utf-8'?>\n<TEI "
    )


def test_the_header_names_the_transcript_and_the_export_date(export_transcript):
    root = parsed(export_transcript)

    assert root.find(f'.//{TEI}titleStmt/{TEI}title').text == 'Interview mit Alice'
    assert '2026-10-18' in root.find(f'.//{TEI}publicationStmt/{TEI}p').text


def test_the_header_describes_the_recording(export_transcript):
    recording = parsed(export_transcript).find(f'.//{TEI}recording')

    assert recording.get('type') == 'audio'
    assert recording.get('dur') == 'PT3600S'
    media = recording.find(f'{TEI}media')
    assert media.get('url') == 'interview.wav'
    assert media.get('mimeType') == 'audio/wav'


def test_a_file_that_is_not_audio_is_a_video_recording(export_transcript):
    root = parsed(export_transcript, media_type='video/mp4')

    assert root.find(f'.//{TEI}recording').get('type') == 'video'


def test_a_zero_duration_omits_only_the_duration(export_transcript):
    recording = parsed(export_transcript, duration=0).find(
        f'.//{TEI}sourceDesc/{TEI}recordingStmt/{TEI}recording'
    )

    assert recording.get('dur') is None
    assert recording.find(f'{TEI}media').get('url') == 'interview.wav'


def test_the_language_is_declared(export_transcript):
    root = parsed(export_transcript)

    assert root.get(XML_LANG) == 'de'
    assert root.find(f'.//{TEI}langUsage/{TEI}language').get('ident') == 'de'


def test_a_null_language_omits_the_language_declarations(export_content):
    export_content['language'] = None
    root = parsed(validate_mmt_content(export_content))

    assert root.get(XML_LANG) is None
    assert root.find(f'.//{TEI}langUsage') is None


def test_every_speaker_is_a_person(export_transcript):
    persons = parsed(export_transcript).findall(f'.//{TEI}listPerson/{TEI}person')

    assert [(p.get(XML_ID), p.find(f'{TEI}persName').text) for p in persons] == [
        ('s1', 'Alice'),
        ('s2', 's2'),
    ]


def test_no_speakers_omits_the_participant_list(export_content):
    export_content['speakers'] = []
    for segment in export_content['segments']:
        segment['speakerId'] = None
        for word in segment['words']:
            word['speakerId'] = None
    root = parsed(validate_mmt_content(export_content))

    assert root.find(f'.//{TEI}particDesc') is None


def test_the_timeline_has_one_point_per_distinct_timestamp(export_transcript):
    timeline = parsed(export_transcript).find(f'.//{TEI}timeline')

    assert timeline.get('unit') == 's'
    assert timeline.get('origin') == '#t0'
    points = [
        (when.get(XML_ID), when.get('absolute'), when.get('interval'))
        for when in timeline.findall(f'{TEI}when')
    ]
    # sg1 ends where sg2 starts, so 4.2 is one point.
    assert points == [
        ('t0', '00:00:00', None),
        ('t1', None, '4.2'),
        ('t2', None, '7.9'),
        ('t3', None, '8.5'),
        ('t4', None, '10'),
    ]
    for when in timeline.findall(f'{TEI}when')[1:]:
        assert when.get('since') == '#t0'


def test_a_segment_not_starting_at_zero_still_has_the_origin(export_content):
    # Only sg3 is kept, so the maps its words do not reference are emptied.
    export_content['segments'] = export_content['segments'][2:]
    export_content['mentions'] = {}
    export_content['entities'] = {}
    export_content['redactions'] = {}
    timeline = parsed(validate_mmt_content(export_content)).find(f'.//{TEI}timeline')

    whens = timeline.findall(f'{TEI}when')
    assert [when.get(XML_ID) for when in whens] == ['t0', 't1', 't2']
    assert whens[1].get('interval') == '8.5'


def test_every_segment_is_an_utterance(export_transcript):
    utterances = parsed(export_transcript).findall(f'.//{TEI}body/{TEI}u')

    assert [
        (u.get(XML_ID), u.get('who'), u.get('start'), u.get('end'), u.text)
        for u in utterances
    ] == [
        ('sg1', '#s1', '#t0', '#t1', 'Hi, wie geht es dir?'),
        ('sg2', '#s2', '#t1', '#t2', 'Ich wohne [redacted]'),
        ('sg3', None, '#t3', '#t4', 'Aha, schön.'),
    ]


def test_markup_characters_are_escaped_by_the_serialiser(export_content):
    export_content['speakers'][0]['name'] = 'A & <B>'
    export_content['segments'][0]['words'][0]['word'] = '<Hi>'
    result = exported(validate_mmt_content(export_content))

    assert b'A &amp; &lt;B&gt;' in result
    root = ET.fromstring(result)
    assert root.find(f'.//{TEI}persName').text == 'A & <B>'
    assert root.find(f'.//{TEI}u').text.startswith('<Hi>')
