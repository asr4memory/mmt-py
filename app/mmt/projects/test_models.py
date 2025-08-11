from datetime import datetime

import pytest
from django.contrib.auth import get_user_model

from .models import Project

User = get_user_model()


@pytest.mark.django_db
def test_normal_directory_name():
    """Directory names are created from title and creation date"""
    user = User.objects.create_user(username="alice", password="password")
    date_now = datetime.now()
    project = Project.objects.create(name="Test project", user=user)

    actual = project.directory_name
    expected = "Test_project" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
    assert actual == expected


@pytest.mark.django_db
def test_unsafe_directory_name():
    """Directory names are made safe"""
    user = User.objects.create_user(username="alice", password="password")
    date_now = datetime.now()
    project = Project.objects.create(name="ä/#*hello", user=user)

    actual = project.directory_name
    expected = "ähello" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")
    assert actual == expected
