from dataclasses import dataclass
from datetime import datetime

from mmt.transcripts.mmt_schema import Transcript


@dataclass(frozen=True)
class ExportContext:
    """Data transfer object holding everything an exporter reads."""

    # mmt_schema.Transcript, not the Django model of the same name.
    transcript: Transcript
    # For the PDF title block and the TEI header.
    label: str
    created_at: datetime
    project_title: str
    filename: str
    media_type: str
    duration: int
