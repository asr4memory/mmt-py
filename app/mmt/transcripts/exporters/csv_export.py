"""Export as CSV: one row per segment, for a spreadsheet.

The module is not named csv.py, so that it cannot shadow the standard
library's csv module.
"""

import csv
import io

from mmt.transcripts.exporters.speakers import speaker_labels_by_id
from mmt.transcripts.exporters.words import segment_text
from mmt.transcripts.mmt_schema import Transcript


def export_to_csv(transcript: Transcript) -> bytes:
    speaker_labels = speaker_labels_by_id(transcript)

    # The default dialect is RFC 4180, with \r\n line endings.
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['index', 'start', 'end', 'speaker', 'text'])

    for index, segment in enumerate(transcript.segments, start=1):
        speaker = (
            speaker_labels[segment.speakerId] if segment.speakerId is not None else ''
        )
        writer.writerow(
            [
                index,
                f'{segment.start:.3f}',
                f'{segment.end:.3f}',
                speaker,
                segment_text(segment, merge_redactions=True),
            ]
        )

    return output.getvalue().encode('utf-8')
