"""Tests for the export views, described in
specs/2026-07-30-transcript-export.md under "Tests".

Only whisperX, WebVTT and SubRip exist at this point; each later slice adds
its format's assertions here.
"""

import json
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
def make_transcript(db):
    def factory(user, content, label='Test transcript'):
        project = create_project(title='Test project', user=user)
        uploaded_file = UploadedFile.objects.create(
            project=project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        return Transcript.objects.create(
            label=label, content=content, uploaded_file=uploaded_file
        )

    return factory


@pytest.fixture
def transcript(make_transcript, alice, export_content):
    return make_transcript(alice, export_content)


def test_whisperx_export_is_a_json_download(client, alice, transcript):
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'application/json'
    assert (
        response['Content-Disposition'] == 'attachment; filename="test_transcript.json"'
    )
    document = json.loads(response.content)
    assert document['language'] == 'de'
    assert len(document['segments']) == 3


def test_vtt_export_is_a_subtitle_download(client, alice, transcript):
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/export/vtt/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'text/vtt; charset=utf-8'
    assert (
        response['Content-Disposition'] == 'attachment; filename="test_transcript.vtt"'
    )
    assert response.content.decode('utf-8').startswith('WEBVTT\n')


def test_srt_export_is_a_subtitle_download(client, alice, transcript):
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/export/srt/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'application/x-subrip; charset=utf-8'
    assert (
        response['Content-Disposition'] == 'attachment; filename="test_transcript.srt"'
    )
    assert response.content.decode('utf-8').startswith('1\n')


def test_export_of_another_users_transcript_is_not_found(client, bob, transcript):
    client.force_login(bob)

    response = client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_export_without_the_view_permission_redirects_to_the_login_page(
    client, db, transcript
):
    carol = User.objects.create_user(
        username='carol',
        password='password',
        email='carol@example.com',
        terms_accepted_version=1,
    )
    client.force_login(carol)

    response = client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.FOUND
    assert response['Location'] == (
        f'/accounts/login/?next=/transcripts/{transcript.pk}/export/whisperx/'
    )


def test_a_label_without_usable_characters_falls_back_to_the_id(
    client, alice, make_transcript, export_content
):
    transcript = make_transcript(alice, export_content, label='...')
    client.force_login(alice)

    response = client.get(f'/transcripts/{transcript.pk}/export/whisperx/')

    assert response.status_code == HTTPStatus.OK
    assert response['Content-Disposition'] == (
        f'attachment; filename="transcript_{transcript.pk}.json"'
    )
