"""Export a transcript's segments as a CSV table.

The module is named ``csv_export`` and not ``csv`` so that it cannot shadow the
standard library's ``csv`` module for anything importing it.

Times are written as seconds and not as ``HH:MM:SS.mmm``: a spreadsheet can
compute a readable timecode from a number, while parsing a timecode string back
into a number needs a formula that most users will not write.
"""

import csv
import io

from mmt.transcripts.exporters.registry import ExportContext

HEADER = ['index', 'start', 'end', 'speaker', 'text']


def export(context: ExportContext) -> bytes:
    transcript = context.transcript
    labels = {speaker.id: speaker.name or speaker.id for speaker in transcript.speakers}

    # newline='' is what the csv module requires of the file it writes to, so
    # that the dialect decides the line ending and the stream does not
    # translate it a second time.
    buffer = io.StringIO(newline='')
    # The default dialect is RFC 4180, which quotes a value containing a comma,
    # a quotation mark or a line break and ends every row with \r\n.
    writer = csv.writer(buffer)
    writer.writerow(HEADER)

    for index, segment in enumerate(transcript.segments, start=1):
        speaker = '' if segment.speakerId is None else labels[segment.speakerId]
        writer.writerow(
            [
                index,
                f'{segment.start:.3f}',
                f'{segment.end:.3f}',
                speaker,
                ' '.join(word.word for word in segment.words),
            ]
        )

    # Encoded with a byte order mark, because Excel otherwise reads a UTF-8 CSV
    # as the system's legacy encoding and shows broken umlauts.
    return buffer.getvalue().encode('utf-8-sig')
