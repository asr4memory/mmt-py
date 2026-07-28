from http import HTTPStatus
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript, TranscriptionJob
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


def make_user(username):
    return User.objects.create_user(
        username=username,
        password='password',
        email=f'{username}@example.com',
        terms_accepted_version=1,
    )


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))


@pytest.fixture
def alice(db):
    user = make_user('alice')
    grant(
        user,
        'view_uploadedfile',
        'add_transcript',
        'view_transcript',
        'add_transcriptionjob',
    )
    return user


@pytest.fixture
def uploaded_file(alice):
    project = create_project(title='Test project', user=alice)
    return UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


@pytest.fixture
def transcribe_url(uploaded_file):
    return reverse('uploaded_files:transcribe', kwargs={'pk': uploaded_file.pk})


@pytest.fixture
def detail_url(uploaded_file):
    return reverse('uploaded_files:detail', kwargs={'pk': uploaded_file.pk})


def test_transcribe_creates_a_job_and_queues_the_submit_task(
    client, alice, uploaded_file, transcribe_url
):
    client.force_login(alice)

    with mock.patch('mmt.uploaded_files.views.submit_transcription_job') as submit:
        response = client.post(transcribe_url, {'language': 'de', 'diarize': 'on'})

    assert response.status_code == HTTPStatus.FOUND

    job = TranscriptionJob.objects.get()
    assert job.uploaded_file == uploaded_file
    assert job.language == 'de'
    assert job.diarize is True
    assert job.status == TranscriptionJob.PENDING
    submit.delay.assert_called_once_with(job.pk)


def test_transcribe_requires_the_permission(client, db, uploaded_file, transcribe_url):
    bob = make_user('bob')
    grant(bob, 'view_uploadedfile')
    uploaded_file.project.user = bob
    uploaded_file.project.save()
    client.force_login(bob)

    response = client.post(transcribe_url, {'language': '', 'diarize': ''})

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert TranscriptionJob.objects.count() == 0


def test_transcribe_action_is_hidden_without_the_permission(
    client, db, uploaded_file, detail_url
):
    bob = make_user('bob')
    grant(bob, 'view_uploadedfile')
    uploaded_file.project.user = bob
    uploaded_file.project.save()
    client.force_login(bob)

    response = client.get(detail_url)

    assert response.status_code == HTTPStatus.OK
    assert b'data-testid="transcribe-form"' not in response.content


def test_transcribe_is_refused_when_the_asr_integration_is_disabled(
    settings, client, alice, uploaded_file, transcribe_url
):
    settings.MMT_ASR_ENABLED = False
    client.force_login(alice)

    with mock.patch('mmt.uploaded_files.views.submit_transcription_job') as submit:
        response = client.post(
            transcribe_url, {'language': 'de', 'diarize': 'on'}, follow=True
        )

    assert TranscriptionJob.objects.count() == 0
    submit.delay.assert_not_called()
    messages = [str(message) for message in response.context['messages']]
    assert messages == ['Transcription is not available.']


def test_the_file_page_hides_the_section_when_the_asr_integration_is_disabled(
    settings, client, alice, uploaded_file, detail_url
):
    settings.MMT_ASR_ENABLED = False
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file, status=TranscriptionJob.RUNNING
    )
    client.force_login(alice)

    content = client.get(detail_url).content.decode()

    assert 'data-testid="transcribe-form"' not in content
    assert 'data-testid="transcription-jobs"' not in content


def test_transcribe_rejects_a_file_of_another_user(client, db, transcribe_url):
    bob = make_user('bob')
    grant(bob, 'view_uploadedfile', 'add_transcriptionjob')
    client.force_login(bob)

    response = client.post(transcribe_url, {'language': '', 'diarize': ''})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert TranscriptionJob.objects.count() == 0


def test_transcribe_rejects_a_file_without_media(
    client, alice, uploaded_file, transcribe_url
):
    uploaded_file.has_file = False
    uploaded_file.save()
    client.force_login(alice)

    response = client.post(transcribe_url, {'language': '', 'diarize': ''}, follow=True)

    assert TranscriptionJob.objects.count() == 0
    messages = [str(message) for message in response.context['messages']]
    assert messages == ['This file cannot be transcribed.']


def test_transcribe_refuses_a_second_running_job(
    client, alice, uploaded_file, transcribe_url
):
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file, status=TranscriptionJob.RUNNING
    )
    client.force_login(alice)

    with mock.patch('mmt.uploaded_files.views.submit_transcription_job') as submit:
        response = client.post(
            transcribe_url, {'language': '', 'diarize': ''}, follow=True
        )

    assert TranscriptionJob.objects.count() == 1
    submit.delay.assert_not_called()
    messages = [str(message) for message in response.context['messages']]
    assert messages == ['This file is already being transcribed.']


def test_the_file_page_shows_job_state(client, alice, uploaded_file, detail_url):
    transcript = Transcript.objects.create(
        uploaded_file=uploaded_file, label='ASR', content={}
    )
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        status=TranscriptionJob.SUCCEEDED,
        progress=1.0,
        transcript=transcript,
    )
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        status=TranscriptionJob.FAILED,
        error='RuntimeError: CUDA out of memory',
    )
    running = TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        status=TranscriptionJob.RUNNING,
        progress=0.42,
    )
    client.force_login(alice)

    content = client.get(detail_url).content.decode()

    assert 'Succeeded' in content
    assert 'Failed' in content
    assert 'RuntimeError: CUDA out of memory' in content
    assert '42' in content
    assert reverse('transcripts:detail', kwargs={'pk': transcript.pk}) in content
    assert running.status == TranscriptionJob.RUNNING


def test_the_file_page_hides_the_trigger_while_a_job_runs(
    client, alice, uploaded_file, detail_url
):
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file, status=TranscriptionJob.RUNNING
    )
    client.force_login(alice)

    content = client.get(detail_url).content.decode()

    assert 'data-testid="transcribe-form"' not in content
    assert 'data-testid="transcription-jobs"' in content
