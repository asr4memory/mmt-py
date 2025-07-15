from datetime import datetime

import pytest
from django.contrib.auth import get_user_model

from .models import UploadJob

User = get_user_model()


@pytest.mark.django_db
def test_normal_directory_name():
    """Directory names are created from title and creation date"""
    user = User.objects.create_user(username="alice", password="password")
    date_now = datetime.now()
    job = UploadJob.objects.create(title="Test upload job", user=user)

    actual = job.directory_name()
    expected = "Test upload job" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
    assert actual == expected


@pytest.mark.django_db
def test_unsafe_directory_name():
    """Directory names are made safe"""
    user = User.objects.create_user(username="alice", password="password")
    date_now = datetime.now()
    job = UploadJob.objects.create(title="ä/#*hello", user=user)

    actual = job.directory_name()
    expected = "ähello" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
    assert actual == expected
