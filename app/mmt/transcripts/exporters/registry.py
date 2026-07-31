"""The exporter registry.

``EXPORT_FORMATS`` is read in two places: the export view resolves the format
key from the URL against it, and the transcript detail page renders its list of
download links from it. Adding a format is therefore one new module in this
package and one entry below, and never a view, route or template change.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from django.utils.translation import gettext_lazy as _

from mmt.transcripts.mmt_schema import Transcript


@dataclass(frozen=True)
class ExportContext:
    """Everything an exporter is allowed to read.

    The transcript is the validated ``mmt_schema.Transcript`` model, not the
    raw content dict and not the Django model, so an exporter reading
    ``segment.start`` cannot silently get ``None`` for a key a raw dict would
    return. The surrounding fields the PDF and the TEI header need are copied
    in, so no exporter touches the database or the request.
    """

    transcript: Transcript
    label: str
    created_at: datetime
    project_title: str
    filename: str
    media_type: str
    duration: int


@dataclass(frozen=True)
class ExportFormat:
    """One downloadable format.

    ``export`` returns ``bytes`` rather than ``str`` so that the encoding
    decision belongs to the format and the view never has to guess one.
    """

    key: str
    name: str
    description: str
    extension: str
    content_type: str
    export: Callable[[ExportContext], bytes]


# Imported below the two dataclasses rather than at the top of the module,
# because every exporter module imports ExportContext from here and the import
# would otherwise be circular.
from mmt.transcripts.exporters import csv_export, srt, vtt, whisperx  # noqa: E402

# Insertion order is the display order on the detail page: the
# machine-readable full-fidelity format first, then the segment formats, then
# the format meant for reading.
EXPORT_FORMATS: dict[str, ExportFormat] = {
    'whisperx': ExportFormat(
        key='whisperx',
        name=_('whisperX JSON'),
        description=_(
            'The full transcript with word-level timestamps, in the shape '
            'whisperX produces.'
        ),
        extension='json',
        content_type='application/json',
        export=whisperx.export,
    ),
    'vtt': ExportFormat(
        key='vtt',
        name=_('WebVTT subtitles'),
        description=_(
            'One subtitle cue per segment, for a video player or a video editor.'
        ),
        extension='vtt',
        content_type='text/vtt; charset=utf-8',
        export=vtt.export,
    ),
    'srt': ExportFormat(
        key='srt',
        name=_('SubRip subtitles'),
        description=_(
            'One numbered subtitle block per segment, in the format most players read.'
        ),
        extension='srt',
        content_type='application/x-subrip; charset=utf-8',
        export=srt.export,
    ),
    'csv': ExportFormat(
        key='csv',
        name=_('CSV table'),
        description=_(
            'One row per segment with its time, speaker and text, for a '
            'spreadsheet or a statistics program.'
        ),
        extension='csv',
        content_type='text/csv; charset=utf-8',
        export=csv_export.export,
    ),
}
