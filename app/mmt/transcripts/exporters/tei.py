"""Export a transcript as a TEI P5 document.

The document is built with ``xml.etree.ElementTree`` and serialised by it, so
escaping is the standard library's responsibility and not a set of format
strings.

The output stops at the segment: one ``<u>`` per segment, no ``<w>`` elements.
Word-level markup is what a word-timestamped TEI would need, and this format
deliberately does not go that far.
"""

import io
from xml.etree import ElementTree

from django.utils import timezone

from mmt.core.utils import file_category
from mmt.transcripts.exporters.registry import ExportContext
from mmt.transcripts.mmt_schema import Transcript

TEI_NS = 'http://www.tei-c.org/ns/1.0'
XML_NS = 'http://www.w3.org/XML/1998/namespace'

XML_ID = f'{{{XML_NS}}}id'
XML_LANG = f'{{{XML_NS}}}lang'

# Serialise TEI elements without a prefix, as the default namespace of the
# document.
ElementTree.register_namespace('', TEI_NS)


def export(context: ExportContext) -> bytes:
    transcript = context.transcript

    root = _element('TEI')
    if transcript.language is not None:
        root.set(XML_LANG, transcript.language)

    _append_header(root, context)

    body = _element('body', parent=_element('text', parent=root))
    # The timeline is built first, because every <u> refers to two of its
    # points by name.
    timestamps = _timestamps(transcript)
    _append_timeline(body, timestamps)
    _append_utterances(body, transcript, timestamps)

    ElementTree.indent(root, space='  ')
    buffer = io.BytesIO()
    ElementTree.ElementTree(root).write(buffer, encoding='utf-8', xml_declaration=True)
    return buffer.getvalue()


def _append_header(root: ElementTree.Element, context: ExportContext) -> None:
    header = _element('teiHeader', parent=root)

    file_desc = _element('fileDesc', parent=header)
    _element(
        'title',
        text=context.label,
        parent=_element('titleStmt', parent=file_desc),
    )
    _element(
        'p',
        text=(
            'Exported from the Media Management Tool on '
            f'{timezone.localdate().isoformat()}.'
        ),
        parent=_element('publicationStmt', parent=file_desc),
    )
    _append_source(file_desc, context)

    _append_profile(header, context)


def _append_source(file_desc: ElementTree.Element, context: ExportContext) -> None:
    source_desc = _element('sourceDesc', parent=file_desc)

    if context.duration == 0:
        # A duration of 0 means the uploaded file was never probed, and
        # dur="PT0S" would assert something false. The file is still named, so
        # that <sourceDesc> is not left empty, which TEI does not allow.
        _element('p', text=context.filename, parent=source_desc)
        return

    recording = _element(
        'recording',
        parent=_element('recordingStmt', parent=source_desc),
    )
    recording.set(
        'type', 'audio' if file_category(context.media_type) == 'audio' else 'video'
    )
    recording.set('dur', f'PT{context.duration}S')

    media = _element('media', parent=recording)
    media.set('url', context.filename)
    media.set('mimeType', context.media_type)


def _append_profile(header: ElementTree.Element, context: ExportContext) -> None:
    transcript = context.transcript
    if transcript.language is None and not transcript.speakers:
        return

    profile_desc = _element('profileDesc', parent=header)

    if transcript.language is not None:
        language = _element(
            'language',
            parent=_element('langUsage', parent=profile_desc),
        )
        language.set('ident', transcript.language)

    if transcript.speakers:
        # An empty <listPerson> is not valid TEI, so the whole participant
        # description is left out when the transcript has no speakers.
        list_person = _element(
            'listPerson',
            parent=_element('particDesc', parent=profile_desc),
        )
        for speaker in transcript.speakers:
            # The mmt speaker ids (s1, s2) are already valid XML names, so they
            # are used unchanged.
            person = _element('person', parent=list_person)
            person.set(XML_ID, speaker.id)
            _element('persName', text=speaker.name or speaker.id, parent=person)


def _timestamps(transcript: Transcript) -> list[float]:
    """The distinct segment boundaries in ascending order.

    A segment that starts exactly where the previous one ends contributes one
    timeline point, not two.
    """
    values = set()
    for segment in transcript.segments:
        values.add(segment.start)
        values.add(segment.end)
    return sorted(values)


def _append_timeline(body: ElementTree.Element, timestamps: list[float]) -> None:
    timeline = _element('timeline', parent=body)
    timeline.set('unit', 's')
    timeline.set('origin', '#t0')

    for index, value in enumerate(timestamps):
        point = _element('when', parent=timeline)
        point.set(XML_ID, f't{index}')
        if index == 0:
            point.set('absolute', '00:00:00')
        else:
            point.set('interval', _interval(value - timestamps[0]))
            point.set('since', '#t0')


def _append_utterances(
    body: ElementTree.Element, transcript: Transcript, timestamps: list[float]
) -> None:
    names = {value: f't{index}' for index, value in enumerate(timestamps)}

    for segment in transcript.segments:
        # The segment's mmt id is exported as its xml:id. TEI needs an
        # identifier here anyway, and reusing the stored one lets a TEI file be
        # traced back to the transcript.
        utterance = _element(
            'u',
            text=' '.join(word.word for word in segment.words),
            parent=body,
        )
        utterance.set(XML_ID, segment.id)
        if segment.speakerId is not None:
            utterance.set('who', f'#{segment.speakerId}')
        utterance.set('start', f'#{names[segment.start]}')
        utterance.set('end', f'#{names[segment.end]}')


def _interval(seconds: float) -> str:
    """Seconds since the origin, with at most three decimal places.

    Trailing zeros are removed, so a boundary at 4.2 seconds is written as
    "4.2" rather than "4.200".
    """
    text = f'{seconds:.3f}'.rstrip('0').rstrip('.')
    return text or '0'


def _element(
    tag: str,
    *,
    text: str | None = None,
    parent: ElementTree.Element | None = None,
) -> ElementTree.Element:
    """A TEI element, appended to its parent when one is given."""
    qualified = f'{{{TEI_NS}}}{tag}'
    element = (
        ElementTree.Element(qualified)
        if parent is None
        else ElementTree.SubElement(parent, qualified)
    )
    element.text = text
    return element
