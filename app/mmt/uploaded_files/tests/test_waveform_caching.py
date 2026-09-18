"""HTTP caching of the waveform JSON view."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils.http import http_date

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile, Waveform

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(
        username=username,
        password='password',
        email=f'{username}@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='view_uploadedfile'))
    return user


@pytest.fixture
def alice(db):
    return make_user('alice')


@pytest.fixture
def bob(db):
    return make_user('bob')


@pytest.fixture
def waveform(db, alice):
    project = create_project(title='Test project', user=alice)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    return Waveform.objects.create(
        uploaded_file=uploaded_file,
        data=[108, 118, 112, 129, 118],
    )


def waveform_url(waveform):
    return f'/uploaded-files/{waveform.uploaded_file_id}/waveform/'


def test_unmodified_waveform_is_answered_without_a_body(client, alice, waveform):
    client.force_login(alice)

    response = client.get(
        waveform_url(waveform),
        headers={'if-modified-since': http_date(waveform.updated_at.timestamp())},
    )

    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.content == b''


def test_conditional_request_of_another_user_is_forbidden(client, bob, waveform):
    """The ownership check must run before the conditional check, so a 304
    cannot confirm the existence or the age of another user's waveform."""
    client.force_login(bob)

    response = client.get(
        waveform_url(waveform),
        headers={'if-modified-since': http_date(waveform.updated_at.timestamp())},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
