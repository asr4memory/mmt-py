"""Tests for the export view.

This is the only export test that needs the database and the client. The
formats themselves are tested against an ExportContext in their own modules.
"""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages

from mmt.projects.use_cases import create_project
from mmt.transcripts.exporters import EXPORT_FORMATS
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

from .conftest import EXPORT_CONTENT

User = get_user_model()

WHISPER_CONTENT = {
    'language': 'en',
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'speaker': 'SPEAKER_00',
            'words': [
                {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'speaker': 'SPEAKER_00'},
                {'word': 'world', 'start': 0.5, 'end': 1.0, 'speaker': 'SPEAKER_00'},
            ],
        }
    ],
}


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
def bob(db):
    user = User.objects.create_user(
        username='bob',
        password='password',
        email='bob@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_transcript'))
    return user


@pytest.fixture
def uploaded_file(alice):
    return UploadedFile.objects.create(
        project=create_project(title='Test project', user=alice),
        filename='interview.wav',
        original_filename='interview.wav',
        has_file=True,
        size=20000,
        media_type='audio/wav',
        duration=3600,
    )


@pytest.fixture
def transcript(uploaded_file):
    return Transcript.objects.create(
        label='Interview mit Alice',
        content=EXPORT_CONTENT,
        uploaded_file=uploaded_file,
    )


@pytest.fixture
def alice_client(client, alice):
    client.force_login(alice)
    return client


@pytest.mark.parametrize('key', list(EXPORT_FORMATS))
def test_every_format_is_downloadable(alice_client, transcript, key):
    export_format = EXPORT_FORMATS[key]

    response = alice_client.get(f'/transcripts/{transcript.pk}/export/{key}/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == export_format.content_type
    assert response['Content-Disposition'] == (
        f'attachment; filename="interview_mit_alice.{export_format.extension}"'
    )
    assert response.content


def test_unknown_format_is_not_found(alice_client, transcript):
    response = alice_client.get(f'/transcripts/{transcript.pk}/export/bogus/')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_nonexistent_transcript_is_not_found(alice_client):
    response = alice_client.get('/transcripts/99999/export/whisperx/')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_another_users_transcript_is_not_found(client, bob, transcript):
    client.force_login(bob)

    response = client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_logged_out_user_is_redirected_to_the_login_page(client, transcript):
    url = f'/transcripts/{transcript.pk}/export/whisperx/'

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response['Location'] == f'/accounts/login/?next={url}'


def test_user_without_the_view_permission_is_redirected(client, db, transcript):
    charlie = User.objects.create_user(
        username='charlie',
        password='password',
        email='charlie@example.com',
        terms_accepted_version=1,
    )
    client.force_login(charlie)
    url = f'/transcripts/{transcript.pk}/export/whisperx/'

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response['Location'] == f'/accounts/login/?next={url}'


def test_invalid_content_redirects_to_the_detail_page_with_an_error(
    alice_client, uploaded_file
):
    invalid = dict(EXPORT_CONTENT)
    del invalid['speakers']
    transcript = Transcript.objects.create(
        label='Broken', content=invalid, uploaded_file=uploaded_file
    )

    response = alice_client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.FOUND
    assert response['Location'] == f'/transcripts/{transcript.pk}/'
    assert [str(message) for message in get_messages(response.wsgi_request)] == [
        'This transcript cannot be exported because its content is invalid. '
        'Please contact an administrator.'
    ]


def test_label_without_usable_characters_falls_back_to_the_transcript_id(
    alice_client, uploaded_file
):
    transcript = Transcript.objects.create(
        label='...', content=EXPORT_CONTENT, uploaded_file=uploaded_file
    )

    response = alice_client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response['Content-Disposition'] == (
        f'attachment; filename="transcript_{transcript.pk}.json"'
    )


def test_legacy_whisper_content_is_exported_without_being_rewritten(
    alice_client, uploaded_file
):
    transcript = Transcript.objects.create(
        label='Legacy', content=WHISPER_CONTENT, uploaded_file=uploaded_file
    )

    response = alice_client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.OK
    transcript.refresh_from_db()
    assert transcript.content == WHISPER_CONTENT


def test_detail_page_lists_every_format(alice_client, transcript):
    response = alice_client.get(f'/transcripts/{transcript.pk}/')

    content = response.content.decode()
    for key, export_format in EXPORT_FORMATS.items():
        assert f'/transcripts/{transcript.pk}/export/{key}/' in content
        assert str(export_format.name) in content
