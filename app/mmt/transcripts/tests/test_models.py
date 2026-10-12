import pytest
from django.contrib.auth import get_user_model

from mmt.projects.models import Project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def transcript(db):
    user = User.objects.create_user(
        username='alice', password='password', email='alice@example.com'
    )
    project = Project.objects.create(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project, filename='interview.mp4'
    )
    return Transcript.objects.create(uploaded_file=uploaded_file, label='Interview')


def test_creating_a_transcript_marks_the_project_changed(
    marks_project_changed, transcript
):
    uploaded_file = transcript.uploaded_file

    with marks_project_changed(uploaded_file.project):
        Transcript.objects.create(uploaded_file=uploaded_file, label='Second')


def test_deleting_a_transcript_marks_the_project_changed(
    marks_project_changed, transcript
):
    with marks_project_changed(transcript.uploaded_file.project):
        transcript.delete()
