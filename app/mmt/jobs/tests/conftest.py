import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import EntityExtractionJob, Transcript, TranscriptionJob
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


def make_user(username):
    return User.objects.create_user(
        username=username,
        password='password',
        email=f'{username}@example.com',
        terms_accepted_version=1,
    )


@pytest.fixture
def alice(db):
    user = make_user('alice')
    user.user_permissions.add(Permission.objects.get(codename='view_transcriptionjob'))
    return user


@pytest.fixture
def bob(db):
    return make_user('bob')


def make_file(user, filename):
    project = create_project(title=f'Project of {filename}', user=user)
    return UploadedFile.objects.create(
        project=project,
        filename=filename,
        original_filename=filename,
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


@pytest.fixture
def make_transcription_job():
    def make(user, filename='interview.mp4', **fields):
        uploaded_file = make_file(user, filename)
        return TranscriptionJob.objects.create(uploaded_file=uploaded_file, **fields)

    return make


@pytest.fixture
def make_extraction_job():
    def make(user, label='Interview transcript', **fields):
        uploaded_file = make_file(user, f'{user.username}_ner.mp4')
        transcript = Transcript.objects.create(
            uploaded_file=uploaded_file, label=label, content={}
        )
        return EntityExtractionJob.objects.create(transcript=transcript, **fields)

    return make
