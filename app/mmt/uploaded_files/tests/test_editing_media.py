"""Tests for the derived media that the transcript editor needs.

The web video and the waveform are only used while editing a transcript, so
they are produced once an uploaded file has its first transcript rather than
right after the upload.
"""

import json
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile, Waveform
from mmt.uploaded_files.tasks import ensure_transcript_editing_media

User = get_user_model()

TRANSCRIPT_CONTENT = {
    'language': 'en',
    'segments': [
        {
            'start': 0.0,
            'end': 1.0,
            'text': 'Hello world',
            'words': [
                {'word': 'Hello', 'start': 0.0, 'end': 0.5},
                {'word': 'world', 'start': 0.5, 'end': 1.0},
            ],
        }
    ],
}


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )


@pytest.fixture
def project(user):
    return create_project(title='Test project', user=user)


@pytest.fixture
def video_file(project):
    return UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


@pytest.fixture
def audio_file(project):
    return UploadedFile.objects.create(
        project=project,
        filename='test_file.wav',
        original_filename='test_file.wav',
        has_file=True,
        size=20000,
        media_type='audio/wav',
    )


@pytest.fixture
def tasks():
    """Both enqueued tasks, patched at their definition site."""
    with (
        mock.patch(
            'mmt.uploaded_files.tasks.task_generate_web_video'
        ) as mock_web_video,
        mock.patch(
            'mmt.uploaded_files.tasks.task_extract_waveform_data'
        ) as mock_waveform,
    ):
        yield mock_web_video, mock_waveform


@pytest.mark.django_db
def test_enqueues_both_tasks_for_a_video_without_derived_media(video_file, tasks):
    mock_web_video, mock_waveform = tasks

    ensure_transcript_editing_media(video_file)

    mock_web_video.delay.assert_called_once_with(video_file.pk)
    mock_waveform.delay.assert_called_once_with(video_file.pk)


@pytest.mark.django_db
def test_enqueues_only_the_waveform_for_audio(audio_file, tasks):
    mock_web_video, mock_waveform = tasks

    ensure_transcript_editing_media(audio_file)

    mock_web_video.delay.assert_not_called()
    mock_waveform.delay.assert_called_once_with(audio_file.pk)


@pytest.mark.django_db
def test_enqueues_nothing_when_both_artifacts_exist(video_file, tasks):
    """Repeated calls are a no-op, so a second transcript does no extra work."""
    mock_web_video, mock_waveform = tasks
    video_file.has_web_video = True
    video_file.save(update_fields=['has_web_video'])
    Waveform.objects.create(uploaded_file=video_file, data=[1, 2, 3])

    ensure_transcript_editing_media(video_file)

    mock_web_video.delay.assert_not_called()
    mock_waveform.delay.assert_not_called()


@pytest.mark.django_db
def test_enqueues_only_the_missing_artifact(video_file, tasks):
    mock_web_video, mock_waveform = tasks
    video_file.has_web_video = True
    video_file.save(update_fields=['has_web_video'])

    ensure_transcript_editing_media(video_file)

    mock_web_video.delay.assert_not_called()
    mock_waveform.delay.assert_called_once_with(video_file.pk)


@pytest.mark.django_db
def test_enqueues_nothing_while_the_file_is_not_assembled(video_file, tasks):
    """Without the assembled file there is nothing to derive the media from.

    Assembly calls this function again once the file is complete.
    """
    mock_web_video, mock_waveform = tasks
    video_file.has_file = False
    video_file.save(update_fields=['has_file'])

    ensure_transcript_editing_media(video_file)

    mock_web_video.delay.assert_not_called()
    mock_waveform.delay.assert_not_called()


@pytest.mark.django_db
def test_enqueues_nothing_for_a_non_media_file(project, tasks):
    mock_web_video, mock_waveform = tasks
    pdf_file = UploadedFile.objects.create(
        project=project,
        filename='paper.pdf',
        original_filename='paper.pdf',
        has_file=True,
        size=20000,
        media_type='application/pdf',
    )

    ensure_transcript_editing_media(pdf_file)

    mock_web_video.delay.assert_not_called()
    mock_waveform.delay.assert_not_called()


@pytest.mark.django_db
def test_creating_a_transcript_triggers_the_editing_media(client, user, video_file):
    user.user_permissions.add(Permission.objects.get(codename='add_transcript'))
    client.login(username='alice', password='password')

    with mock.patch(
        'mmt.uploaded_files.views.ensure_transcript_editing_media'
    ) as mock_ensure:
        client.post(
            f'/uploaded-files/{video_file.id}/create-transcript/',
            {
                'label': 'Test transcript',
                'content': json.dumps(TRANSCRIPT_CONTENT),
            },
        )

    mock_ensure.assert_called_once_with(video_file)
