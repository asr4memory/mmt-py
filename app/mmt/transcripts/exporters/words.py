"""The text an exporter writes for a word."""

from mmt.transcripts.mmt_schema import Word

REDACTION_MARKER = 'XXX'


def word_text(word: Word) -> str:
    """The word as it is exported: the marker when it is redacted.

    One marker per word, so the word keeps its own timings and the segment
    keeps its word count.
    """
    if word.redactionId is not None:
        return REDACTION_MARKER

    return word.word
