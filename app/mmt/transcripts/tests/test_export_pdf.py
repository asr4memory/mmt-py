"""Tests for the PDF exporter.

The layout is asserted on the rendered HTML rather than on the PDF bytes,
because the bytes carry no readable structure. The PDF itself is only checked
for being a PDF, which is what WeasyPrint is responsible for.
"""

import re
from dataclasses import replace

import pytest

from mmt.transcripts.exporters import pdf
from mmt.transcripts.mmt_schema import Transcript


@pytest.fixture
def html(export_context):
    return pdf.render_html(export_context)


def spans(html, class_name):
    return re.findall(f'<span class="{class_name}">(.*?)</span>', html)


def test_export_returns_a_pdf(export_context):
    result = pdf.export(export_context)

    assert result.startswith(b'%PDF-')
    assert len(result) > 1000


def test_the_title_block_names_the_transcript_the_project_and_the_file(html):
    assert 'Interview mit Alice' in html
    assert 'Test project' in html
    assert 'interview.wav' in html


def test_the_title_block_names_the_creation_date(html):
    assert 'July 30, 2026' in html


def test_the_title_block_names_the_language(html):
    assert 'de' in spans(html, 'meta__value')


def test_a_null_language_leaves_the_language_out_of_the_title_block(
    export_content, export_context
):
    export_content['language'] = None
    context = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    html = pdf.render_html(context)

    assert 'de' not in spans(html, 'meta__value')


def test_one_block_per_speaker_turn_with_its_start_time(html):
    assert spans(html, 'turn__time') == ['00:00:00', '00:00:04', '00:00:07']


def test_a_turn_shows_the_speaker_name_falling_back_to_the_speaker_id(html):
    assert spans(html, 'turn__speaker') == ['Alice', 's2']


def test_a_turn_without_a_speaker_shows_no_name(html):
    """The third turn has no speaker, so only two of the three carry a name."""
    assert len(spans(html, 'turn__time')) == 3
    assert len(spans(html, 'turn__speaker')) == 2


def test_the_turn_text_joins_the_words_of_every_segment_in_the_turn(
    export_content, export_context
):
    export_content['segments'][1]['speakerId'] = 's1'
    for word in export_content['segments'][1]['words']:
        word['speakerId'] = 's1'
    context = replace(
        export_context, transcript=Transcript.model_validate(export_content)
    )

    html = pdf.render_html(context)

    assert spans(html, 'turn__time') == ['00:00:00', '00:00:07']
    assert 'Hi, wie geht’s? Und dir?' in html


def test_markup_characters_in_the_text_are_escaped_by_the_template(html):
    assert 'Ähm, &lt;gut&gt;' in html
