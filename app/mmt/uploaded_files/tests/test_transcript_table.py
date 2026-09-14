"""Tests for the transcript table on the uploaded file detail page, described
in specs/2026-09-14-transcript-statistics.md.
"""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
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
    user.user_permissions.add(
        Permission.objects.get(codename='view_uploadedfile'),
        Permission.objects.get(codename='view_transcript'),
        # The detail template gates the transcript section on this permission.
        Permission.objects.get(codename='add_transcript'),
    )
    return user


@pytest.fixture
def uploaded_file(db, alice):
    project = create_project(title='Test project', user=alice)
    return UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


# A document with the three values the table shows: a language, no model key
# at all, and two segments.
CONTENT = {
    'format': 'mmt-transcript',
    'version': 1,
    'language': 'de',
    'speakers': [],
    'entities': {},
    'mentions': {},
    'redactions': {},
    'segments': [
        {
            'id': 'sg1',
            'start': 0.0,
            'end': 1.0,
            'speakerId': None,
            'words': [
                {
                    'id': 'w1',
                    'start': 0.0,
                    'end': 1.0,
                    'word': 'Hallo',
                    'score': 1.0,
                }
            ],
        },
        {
            'id': 'sg2',
            'start': 1.0,
            'end': 2.0,
            'speakerId': None,
            'words': [
                {
                    'id': 'w2',
                    'start': 1.0,
                    'end': 2.0,
                    'word': 'Welt',
                    'score': 1.0,
                }
            ],
        },
    ],
}


@pytest.fixture
def transcript(uploaded_file):
    return Transcript.objects.create(
        label='Test transcript', content=CONTENT, uploaded_file=uploaded_file
    )


def test_the_table_shows_the_annotated_values(client, alice, uploaded_file, transcript):
    client.force_login(alice)

    response = client.get(f'/uploaded-files/{uploaded_file.pk}/')

    assert response.status_code == HTTPStatus.OK
    row = response.context['transcripts'][0]
    assert row.language == 'de'
    assert row.model is None
    assert row.segment_count == 2
    html = response.content.decode()
    assert '<td>de</td>' in html
    assert '<td>2</td>' in html


def test_the_table_renders_an_em_dash_for_a_missing_value(
    client, alice, uploaded_file, transcript
):
    Transcript.objects.filter(pk=transcript.pk).update(content={})
    client.force_login(alice)

    response = client.get(f'/uploaded-files/{uploaded_file.pk}/')

    assert response.status_code == HTTPStatus.OK
    assert response.content.decode().count('<td>—</td>') == 3


def test_the_table_does_not_load_the_content(client, alice, uploaded_file, transcript):
    client.force_login(alice)

    response = client.get(f'/uploaded-files/{uploaded_file.pk}/')

    for row in response.context['transcripts']:
        assert 'content' in row.get_deferred_fields()
