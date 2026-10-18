"""Export the stored mmt-transcript document, unredacted."""

import json

from mmt.transcripts.mmt_schema import Transcript


def export_to_mmt(transcript: Transcript) -> bytes:
    document = transcript.model_dump()
    return json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8')
