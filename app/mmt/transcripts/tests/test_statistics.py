"""Tests for the derived transcript statistics, described in
specs/2026-09-14-transcript-statistics.md.
"""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.transcripts.statistics import derive_statistics
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def alice(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_transcript'))
    return user


@pytest.fixture
def transcript(db, alice, export_content):
    project = create_project(title='Test project', user=alice)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    return Transcript.objects.create(
        label='Test transcript', content=export_content, uploaded_file=uploaded_file
    )


def test_the_values_of_a_stored_document(export_content):
    statistics = derive_statistics(export_content)

    assert statistics == {
        'language': 'de',
        # The export fixture predates the model field and does not carry it.
        'model': None,
        'speaker_count': 2,
        'segment_count': 3,
        'word_count': 11,
        'mention_count': 2,
        'entity_count': 1,
        'redaction_count': 1,
    }


def test_every_value_of_an_empty_document_is_none():
    statistics = derive_statistics({})

    assert set(statistics) == {
        'language',
        'model',
        'speaker_count',
        'segment_count',
        'word_count',
        'mention_count',
        'entity_count',
        'redaction_count',
    }
    assert all(value is None for value in statistics.values())


@pytest.mark.parametrize('content', [None, [], 'mmt-transcript', 7])
def test_content_that_is_not_a_mapping_yields_none(content):
    statistics = derive_statistics(content)

    assert all(value is None for value in statistics.values())


def test_empty_collections_count_as_zero():
    content = {
        'language': None,
        'model': None,
        'speakers': [],
        'entities': {},
        'mentions': {},
        'redactions': {},
        'segments': [],
    }

    statistics = derive_statistics(content)

    assert statistics == {
        'language': None,
        'model': None,
        'speaker_count': 0,
        'segment_count': 0,
        'word_count': 0,
        'mention_count': 0,
        'entity_count': 0,
        'redaction_count': 0,
    }


def test_a_collection_of_the_wrong_type_yields_none():
    statistics = derive_statistics({'speakers': 'Alice', 'segments': 'one'})

    assert statistics['speaker_count'] is None
    assert statistics['segment_count'] is None
    assert statistics['word_count'] is None


def test_the_detail_page_shows_the_counts(client, alice, transcript):
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/')

    assert response.status_code == HTTPStatus.OK
    assert response.context['statistics']['segment_count'] == 3
    assert response.context['statistics']['word_count'] == 11
    html = response.content.decode()
    assert 'Segments' in html
    assert 'Words' in html
    assert '>11<' in html


def test_the_detail_page_renders_an_em_dash_for_a_missing_value(
    client, alice, transcript
):
    transcript.content = {}
    transcript.save()
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/')

    assert response.status_code == HTTPStatus.OK
    assert all(value is None for value in response.context['statistics'].values())
    assert '—' in response.content.decode()
