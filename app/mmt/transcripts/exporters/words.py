"""The text an exporter writes for a word and for a segment."""

from mmt.transcripts.mmt_schema import Segment, Word

REDACTION_MARKER = '[redacted]'


def word_text(word: Word) -> str:
    """The word as it is exported: the marker when it is redacted.

    One marker per word, so the word keeps its own timings and the segment
    keeps its word count.
    """
    if word.redactionId is not None:
        return REDACTION_MARKER

    return word.word


def segment_text(segment: Segment, *, merge_redactions: bool) -> str:
    """The segment's words joined with a single space.

    With merge_redactions, a run of consecutive words of the same redaction is
    one marker instead of one marker per word.
    """
    texts = []
    previous_redaction_id = None
    for word in segment.words:
        continues_run = (
            word.redactionId is not None and word.redactionId == previous_redaction_id
        )
        if not (merge_redactions and continues_run):
            texts.append(word_text(word))
        previous_redaction_id = word.redactionId

    # The word tokens carry their trailing punctuation, so a plain join
    # reproduces the original spacing.
    return ' '.join(texts)
