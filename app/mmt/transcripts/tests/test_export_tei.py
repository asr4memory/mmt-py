"""Tests for the TEI XML exporter.

The exporter builds the document with ``xml.etree.ElementTree``, so escaping is
the standard library's responsibility. The tests parse the result rather than
matching on strings, because the point of the format is that a TEI processor
can read it.
"""

from dataclasses import replace
from xml.etree import ElementTree

import pytest
from django.utils import timezone

from mmt.transcripts.exporters import tei
from mmt.transcripts.mmt_schema import Transcript

TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'

XML_ID = f'{{{XML_NS}}}id'
XML_LANG = f'{{{XML_NS}}}lang'


@pytest.fixture
def exported(export_context):
    return tei.export(export_context)


@pytest.fixture
def root(exported):
    return ElementTree.fromstring(exported.decode())


def context_with(export_context, content):
    """A copy of the context carrying the given content as its transcript."""
    return replace(export_context, transcript=Transcript.model_validate(content))


def find(element, path):
    return element.find(path.replace('/', f'/{{{TEI_NS}}}').lstrip('/'))


def findall(element, path):
    return element.findall(path.replace('/', f'/{{{TEI_NS}}}').lstrip('/'))


def test_returns_bytes_with_an_xml_declaration(exported):
    assert isinstance(exported, bytes)
    assert exported.startswith(b'<?xml version=')
    assert b"encoding='utf-8'" in exported


def test_the_root_element_is_tei_in_the_tei_namespace(root):
    assert root.tag == f'{{{TEI_NS}}}TEI'


def test_the_root_element_carries_the_content_language(root):
    assert root.get(XML_LANG) == 'de'


def test_the_title_is_the_transcript_label(root):
    assert (
        find(root, '/teiHeader/fileDesc/titleStmt/title').text == 'Interview mit Alice'
    )


def test_the_publication_statement_names_the_export_date(root):
    paragraph = find(root, '/teiHeader/fileDesc/publicationStmt/p')

    assert paragraph.text == (
        'Exported from the Media Management Tool on '
        f'{timezone.localdate().isoformat()}.'
    )


def test_the_recording_carries_the_category_and_the_duration(root):
    recording = find(root, '/teiHeader/fileDesc/sourceDesc/recordingStmt/recording')

    assert recording.get('type') == 'audio'
    assert recording.get('dur') == 'PT3600S'


def test_a_video_file_is_recorded_as_a_video(export_context):
    context = replace(export_context, media_type='video/mp4')

    root = ElementTree.fromstring(tei.export(context).decode())

    recording = find(root, '/teiHeader/fileDesc/sourceDesc/recordingStmt/recording')
    assert recording.get('type') == 'video'


def test_the_media_element_carries_the_filename_and_the_media_type(root):
    media = find(root, '/teiHeader/fileDesc/sourceDesc/recordingStmt/recording/media')

    assert media.get('url') == 'interview.wav'
    assert media.get('mimeType') == 'audio/wav'


def test_a_zero_duration_omits_the_recording_statement(export_context):
    """dur="PT0S" would assert something false."""
    context = replace(export_context, duration=0)

    root = ElementTree.fromstring(tei.export(context).decode())

    assert find(root, '/teiHeader/fileDesc/sourceDesc/recordingStmt') is None


def test_a_zero_duration_leaves_the_source_description_naming_the_file(export_context):
    """An empty <sourceDesc> is not valid TEI."""
    context = replace(export_context, duration=0)

    root = ElementTree.fromstring(tei.export(context).decode())

    assert find(root, '/teiHeader/fileDesc/sourceDesc/p').text == 'interview.wav'


def test_the_language_is_declared_once(root):
    languages = findall(root, '/teiHeader/profileDesc/langUsage/language')

    assert [language.get('ident') for language in languages] == ['de']


def test_a_null_language_omits_the_language_block_and_the_language_attribute(
    export_content, export_context
):
    export_content['language'] = None

    root = ElementTree.fromstring(
        tei.export(context_with(export_context, export_content)).decode()
    )

    assert find(root, '/teiHeader/profileDesc/langUsage') is None
    assert root.get(XML_LANG) is None


def test_every_speaker_becomes_a_person_carrying_its_id(root):
    people = findall(root, '/teiHeader/profileDesc/particDesc/listPerson/person')

    assert [person.get(XML_ID) for person in people] == ['s1', 's2']


def test_a_person_name_falls_back_to_the_speaker_id_when_the_name_is_empty(root):
    people = findall(root, '/teiHeader/profileDesc/particDesc/listPerson/person')

    assert [find(person, '/persName').text for person in people] == ['Alice', 's2']


def test_a_transcript_without_speakers_omits_the_participant_list(
    export_content, export_context
):
    """An empty <listPerson> is not valid TEI."""
    export_content['speakers'] = []
    for segment in export_content['segments']:
        segment['speakerId'] = None
        for word in segment['words']:
            word['speakerId'] = None

    root = ElementTree.fromstring(
        tei.export(context_with(export_context, export_content)).decode()
    )

    assert find(root, '/teiHeader/profileDesc/particDesc') is None


def test_the_timeline_holds_one_point_per_distinct_timestamp_in_ascending_order(root):
    points = findall(root, '/text/body/timeline/when')

    assert [point.get(XML_ID) for point in points] == ['t0', 't1', 't2', 't3']


def test_the_first_point_is_the_origin(root):
    timeline = find(root, '/text/body/timeline')
    first = findall(root, '/text/body/timeline/when')[0]

    assert timeline.get('unit') == 's'
    assert timeline.get('origin') == '#t0'
    assert first.get('absolute') == '00:00:00'
    assert first.get('interval') is None


def test_every_other_point_is_an_interval_since_the_origin(root):
    points = findall(root, '/text/body/timeline/when')[1:]

    assert [point.get('interval') for point in points] == ['4.2', '7.9', '12.346']
    assert {point.get('since') for point in points} == {'#t0'}


def test_a_timestamp_shared_by_two_segments_produces_one_point(root):
    """Three segments meeting end to start have four boundaries, not six."""
    assert len(findall(root, '/text/body/timeline/when')) == 4


def test_one_utterance_per_segment_carrying_the_segment_id(root):
    utterances = findall(root, '/text/body/u')

    assert [utterance.get(XML_ID) for utterance in utterances] == [
        'seg_1',
        'seg_2',
        'seg_3',
    ]


def test_an_utterance_refers_to_its_speaker_and_to_its_two_timeline_points(root):
    first, second, third = findall(root, '/text/body/u')

    assert (first.get('who'), first.get('start'), first.get('end')) == (
        '#s1',
        '#t0',
        '#t1',
    )
    assert (second.get('who'), second.get('start'), second.get('end')) == (
        '#s2',
        '#t1',
        '#t2',
    )
    assert (third.get('start'), third.get('end')) == ('#t2', '#t3')


def test_a_segment_without_a_speaker_carries_no_who_attribute(root):
    third = findall(root, '/text/body/u')[2]

    assert third.get('who') is None


def test_every_reference_resolves_to_an_element_in_the_document(root):
    identifiers = {
        element.get(XML_ID) for element in root.iter() if element.get(XML_ID)
    }

    for utterance in findall(root, '/text/body/u'):
        for attribute in ('who', 'start', 'end'):
            reference = utterance.get(attribute)
            if reference is not None:
                assert reference.removeprefix('#') in identifiers


def test_the_utterance_text_joins_the_words_with_a_single_space(root):
    first = findall(root, '/text/body/u')[0]

    assert first.text == 'Hi, wie geht’s?'


def test_markup_characters_in_the_text_are_escaped_by_the_serialiser(exported, root):
    third = findall(root, '/text/body/u')[2]

    assert third.text == 'Ähm, <gut>'
    assert '&lt;gut&gt;'.encode() in exported


def test_markup_characters_in_a_speaker_name_are_escaped_by_the_serialiser(
    export_content, export_context
):
    export_content['speakers'][0]['name'] = 'Alice & <Bob>'

    exported = tei.export(context_with(export_context, export_content))

    root = ElementTree.fromstring(exported.decode())
    person = findall(root, '/teiHeader/profileDesc/particDesc/listPerson/person')[0]
    assert find(person, '/persName').text == 'Alice & <Bob>'
    assert b'Alice &amp; &lt;Bob&gt;' in exported


def test_there_are_no_word_elements(root):
    assert findall(root, '/text/body/u/w') == []


def test_umlauts_are_encoded_as_utf8(exported):
    assert 'Ähm,'.encode() in exported
