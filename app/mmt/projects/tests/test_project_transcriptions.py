from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript, TranscriptionJob
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))


@pytest.fixture
def alice(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    grant(
        user,
        'view_uploadedfile',
        'view_transcript',
        'add_transcriptionjob',
    )
    return user


@pytest.fixture
def project(alice):
    return create_project(title='Test project', user=alice)


@pytest.fixture
def detail_url(project):
    return reverse('projects:detail', kwargs={'pk': project.pk})


def make_file(project, filename):
    return UploadedFile.objects.create(
        project=project,
        filename=filename,
        original_filename=filename,
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


def test_the_file_table_shows_the_transcript_count(
    client, alice, project, detail_url
):
    with_transcripts = make_file(project, 'with_transcripts.mp4')
    make_file(project, 'without_transcripts.mp4')
    for label in ('ASR', 'Manual'):
        Transcript.objects.create(
            uploaded_file=with_transcripts, label=label, content={}
        )
    client.force_login(alice)

    response = client.get(detail_url)
    content = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assert 'Transcripts' in content
    assert '<td class="table__number">2</td>' in content
    assert '<td class="table__number">-</td>' in content


def test_the_transcript_column_is_hidden_without_the_permission(
    client, alice, project, detail_url
):
    uploaded_file = make_file(project, 'with_transcripts.mp4')
    Transcript.objects.create(uploaded_file=uploaded_file, label='ASR', content={})
    alice.user_permissions.remove(
        Permission.objects.get(codename='view_transcript')
    )
    client.force_login(alice)

    content = client.get(detail_url).content.decode()

    assert 'Transcripts' not in content
    assert '<td class="table__number">1</td>' not in content


def test_the_project_page_lists_running_jobs(client, alice, project, detail_url):
    uploaded_file = make_file(project, 'interview.mp4')
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        status=TranscriptionJob.RUNNING,
        progress=0.42,
    )

    other_project = create_project(title='Other project', user=alice)
    other_file = make_file(other_project, 'other.mp4')
    TranscriptionJob.objects.create(
        uploaded_file=other_file, status=TranscriptionJob.RUNNING
    )

    client.force_login(alice)
    content = client.get(detail_url).content.decode()

    assert 'Transcriptions' in content
    assert 'interview.mp4' in content
    assert '42 %' in content
    assert 'other.mp4' not in content


def test_terminal_jobs_are_not_listed(client, alice, project, detail_url):
    uploaded_file = make_file(project, 'interview.mp4')
    TranscriptionJob.objects.create(
        uploaded_file=uploaded_file,
        status=TranscriptionJob.SUCCEEDED,
        progress=1.0,
    )
    client.force_login(alice)

    content = client.get(detail_url).content.decode()

    assert 'Transcriptions' not in content
