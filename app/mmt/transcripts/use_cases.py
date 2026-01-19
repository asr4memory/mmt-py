from typing import Optional

from mmt.transcripts.models import Transcript


def create_transcript(**kwargs) -> tuple[bool, Optional[Transcript]]:
    """
    Create a transcript using (form) data and an uploaded file object.
    Returns a tuple with a success boolean and the transcript, if it was created.
    """
    try:
        transcript = Transcript.objects.create(**kwargs)
        return (True, transcript)
    except Exception as e:
        return (False, None)
