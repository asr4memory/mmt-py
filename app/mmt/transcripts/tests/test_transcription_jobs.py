import pytest
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import TranscriptionJob
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        filename='interview.mp4', media_type='video/mp4', project=project
    )


def test_media_path_is_relative_to_the_user_files_dir(uploaded_file):
    job = TranscriptionJob.objects.create(uploaded_file=uploaded_file)

    project = uploaded_file.project
    assert job.media_path == f'bob/{project.directory_name}/upload/interview.mp4'
    assert not job.media_path.startswith('/')


def test_a_new_job_is_pending_with_no_service_id(uploaded_file):
    job = TranscriptionJob.objects.create(uploaded_file=uploaded_file)

    assert job.status == TranscriptionJob.PENDING
    assert job.asr_job_id == ''
    assert job.progress == 0.0
    assert job.error == ''
    assert job.language == ''
    assert job.diarize is False
    assert job.transcript is None
    assert job.started_at is None
    assert job.finished_at is None


@pytest.mark.parametrize(
    'status,expected',
    [
        (TranscriptionJob.PENDING, False),
        (TranscriptionJob.SUBMITTED, False),
        (TranscriptionJob.RUNNING, False),
        (TranscriptionJob.SUCCEEDED, True),
        (TranscriptionJob.FAILED, True),
    ],
)
def test_is_terminal_covers_succeeded_and_failed_only(uploaded_file, status, expected):
    job = TranscriptionJob.objects.create(uploaded_file=uploaded_file, status=status)

    assert job.is_terminal is expected
