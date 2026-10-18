"""Export as TEI XML: one utterance per segment on a timeline, for a corpus."""

import datetime
import xml.etree.ElementTree as ET

from mmt.media.media_types import MediaKind, media_kind
from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.words import segment_text
from mmt.transcripts.mmt_schema import Transcript

TEI_NAMESPACE = 'http://www.tei-c.org/ns/1.0'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

ET.register_namespace('', TEI_NAMESPACE)


def export_to_tei(
    transcript: Transcript,
    *,
    title: str,
    media_filename: str,
    media_type: str,
    duration: int,
    export_date: datetime.date,
) -> bytes:
    root = _element('TEI')
    if transcript.language is not None:
        root.set(XML_LANG, transcript.language)

    header = _sub(root, 'teiHeader')
    file_desc = _sub(header, 'fileDesc')
    _sub(_sub(file_desc, 'titleStmt'), 'title').text = title
    _sub(
        _sub(file_desc, 'publicationStmt'), 'p'
    ).text = f'Exported from the Media Management Tool on {export_date.isoformat()}.'
    _add_recording(_sub(file_desc, 'sourceDesc'), media_filename, media_type, duration)

    profile_desc = _sub(header, 'profileDesc')
    if transcript.language is not None:
        _sub(_sub(profile_desc, 'langUsage'), 'language', ident=transcript.language)
    if transcript.speakers:
        _add_speakers(profile_desc, transcript)

    body = _sub(_sub(root, 'text'), 'body')
    point_ids = _add_timeline(body, transcript)
    for segment in transcript.segments:
        utterance = _sub(
            body,
            'u',
            start=f'#{point_ids[segment.start]}',
            end=f'#{point_ids[segment.end]}',
        )
        # The mmt id is kept, so a TEI file can be traced back to the transcript.
        utterance.set(XML_ID, segment.id)
        if segment.speakerId is not None:
            utterance.set('who', f'#{segment.speakerId}')
        utterance.text = segment_text(segment, merge_redactions=True)

    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'


def _add_recording(
    source_desc: ET.Element, media_filename: str, media_type: str, duration: int
) -> None:
    kind = 'audio' if media_kind(media_type) == MediaKind.AUDIO else 'video'
    # Always written, because TEI requires sourceDesc to have content.
    recording = _sub(_sub(source_desc, 'recordingStmt'), 'recording', type=kind)
    # dur="PT0S" would state that the recording has no length.
    if duration > 0:
        recording.set('dur', f'PT{duration}S')
    _sub(recording, 'media', url=media_filename, mimeType=media_type)


def _add_speakers(profile_desc: ET.Element, transcript: Transcript) -> None:
    speaker_labels = speaker_labels_by_id(transcript)
    list_person = _sub(_sub(profile_desc, 'particDesc'), 'listPerson')
    for speaker in transcript.speakers:
        person = _sub(list_person, 'person')
        person.set(XML_ID, speaker.id)
        _sub(person, 'persName').text = speaker_labels[speaker.id]


def _add_timeline(body: ET.Element, transcript: Transcript) -> dict[float, str]:
    """Write one point per distinct segment boundary; map each time to its id.

    The origin t0 is at zero seconds, whether or not a segment starts there.
    """
    times = {0.0}
    for segment in transcript.segments:
        times.add(segment.start)
        times.add(segment.end)

    timeline = _sub(body, 'timeline', unit='s', origin='#t0')
    point_ids = {}
    for index, time in enumerate(sorted(times)):
        point_id = f't{index}'
        point_ids[time] = point_id
        if index == 0:
            when = _sub(timeline, 'when', absolute='00:00:00')
        else:
            when = _sub(timeline, 'when', interval=_seconds(time), since='#t0')
        when.set(XML_ID, point_id)

    return point_ids


def _seconds(time: float) -> str:
    """Seconds with at most three decimal places and no trailing zeros."""
    return f'{time:.3f}'.rstrip('0').rstrip('.')


def _element(tag: str, **attributes: str) -> ET.Element:
    return ET.Element(f'{{{TEI_NAMESPACE}}}{tag}', attributes)


def _sub(parent: ET.Element, tag: str, **attributes: str) -> ET.Element:
    return ET.SubElement(parent, f'{{{TEI_NAMESPACE}}}{tag}', attributes)
