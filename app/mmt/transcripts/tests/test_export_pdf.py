import datetime

import pytest

from mmt.transcripts.exporters import export_to_pdf
from mmt.transcripts.exporters.pdf import render_pdf_html
from mmt.transcripts.mmt_schema import validate_mmt_content

ARGUMENTS = {
    'label': 'Interview mit Alice',
    'project_title': 'Oral History',
    'filename': 'interview.wav',
    'created_at': datetime.datetime(2026, 10, 18, 9, 30, tzinfo=datetime.UTC),
}


@pytest.fixture
def html(export_transcript):
    return render_pdf_html(export_transcript, **ARGUMENTS)


def test_the_result_is_a_pdf(export_transcript):
    result = export_to_pdf(export_transcript, **ARGUMENTS)

    assert result.startswith(b'%PDF-')
    assert len(result) > 5000


def test_the_title_block_names_the_transcript_and_its_source(html):
    assert '<h1>Interview mit Alice</h1>' in html
    assert 'Oral History' in html
    assert 'interview.wav' in html
    # SHORT_DATE_FORMAT of the default language, English.
    assert '10/18/2026' in html
    assert 'Language' in html


def test_every_turn_shows_its_start_speaker_and_text(html):
    assert '00:00:04' in html
    assert 'Alice' in html
    assert 'Ich wohne [redacted]' in html


def test_a_speaker_without_a_name_is_shown_by_id(html):
    assert '>s2<' in html


def test_a_turn_without_a_speaker_shows_no_name(html):
    turn = html[html.index('00:00:08') :]
    turn = turn[: turn.index('</section>')]

    assert 'turn__speaker' not in turn
    assert 'Aha, schön.' in turn


def test_a_null_language_omits_the_language(export_content):
    export_content['language'] = None
    html = render_pdf_html(validate_mmt_content(export_content), **ARGUMENTS)

    assert 'Language' not in html
