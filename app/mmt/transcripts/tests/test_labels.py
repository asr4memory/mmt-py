from datetime import UTC, datetime

from mmt.transcripts.labels import ASR, NER, transcript_label


def test_label_names_the_process_and_the_local_creation_time():
    created_at = datetime(2026, 11, 2, 13, 5, tzinfo=UTC)

    assert transcript_label(ASR, created_at) == 'ASR (2026-11-02 14:05)'
    assert transcript_label(NER, created_at) == 'NER (2026-11-02 14:05)'


def test_label_uses_summer_time_in_the_configured_time_zone():
    created_at = datetime(2026, 7, 2, 12, 5, tzinfo=UTC)

    assert transcript_label(ASR, created_at) == 'ASR (2026-07-02 14:05)'
