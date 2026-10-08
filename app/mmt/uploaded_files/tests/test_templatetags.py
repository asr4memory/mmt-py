from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileChunk, UploadedFile
from mmt.uploaded_files.templatetags.uploaded_files_extras import (
    recent_upload_activity,
    status_label,
)

User = get_user_model()


def test_status_label_known_values():
    assert status_label('missing') == 'Missing'
    assert status_label('incomplete') == 'Incomplete'
    assert status_label('processing') == 'Processing'
    assert status_label('complete') == 'Complete'
    assert status_label('corrupt') == 'Corrupt'


def test_status_label_falls_back_to_value():
    assert status_label('unknown') == 'unknown'


@pytest.fixture
def project():
    bob = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    project = create_project(title='Test project', user=bob)
    return project


@pytest.fixture
def uploaded_file(project):
    return UploadedFile.objects.create(
        filename='video.mp4', media_type='video/mp4', project=project
    )


@pytest.mark.django_db
def test_no_chunks(uploaded_file):
    assert recent_upload_activity() is False


@pytest.mark.django_db
def test_recently_received_chunk(uploaded_file):
    FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
    assert recent_upload_activity() is True


@pytest.mark.django_db
def test_chunk_received_over_5_minutes_ago(uploaded_file):
    chunk = FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
    FileChunk.objects.filter(pk=chunk.pk).update(
        created_at=timezone.now() - timedelta(minutes=6)
    )
    assert recent_upload_activity() is False
