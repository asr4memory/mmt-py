from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.templatetags.uploaded_files_extras import recent_upload_activity

User = get_user_model()


@pytest.fixture
def project():
    bob = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    _, project = create_project(title='Test project', user=bob)
    return project


@pytest.mark.django_db
def test_no_files():
    assert recent_upload_activity() is False


@pytest.mark.django_db
def test_recently_created_file(project):
    UploadedFile.objects.create(
        filename='recent.mp4', media_type='video/mp4', project=project
    )
    assert recent_upload_activity() is True


@pytest.mark.django_db
def test_file_updated_over_5_minutes_ago(project):
    f = UploadedFile.objects.create(
        filename='old.mp4', media_type='video/mp4', project=project
    )
    UploadedFile.objects.filter(pk=f.pk).update(
        updated_at=timezone.now() - timedelta(minutes=6)
    )
    assert recent_upload_activity() is False


@pytest.mark.django_db
def test_completed_upload_still_counts(project):
    """has_file=True should not exclude a recently updated file."""
    UploadedFile.objects.create(
        filename='done.mp4', media_type='video/mp4', project=project, has_file=True
    )
    assert recent_upload_activity() is True
