"""HTTP caching of the media stream view."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils.http import http_date

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

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
def video(db, alice):
    project = create_project(title='Test project', user=alice)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='recording.mov',
        original_filename='recording.mov',
        has_file=True,
        size=len(b'original bytes'),
        media_type='video/quicktime',
    )
    uploaded_file.file_path.write_bytes(b'original bytes')

    yield uploaded_file

    uploaded_file.file_path.unlink(missing_ok=True)


def stream_url(uploaded_file):
    return f'/uploaded-files/{uploaded_file.id}/stream/'


def test_stream_is_cached_by_the_browser_only(client, alice, video):
    """A file only its owner may read must not be stored by a shared cache."""
    client.force_login(alice)

    response = client.get(stream_url(video))

    assert 'private' in response['Cache-Control']
    assert 'public' not in response['Cache-Control']


def test_unmodified_stream_is_answered_without_a_body(client, alice, video):
    """The file's mtime lets the browser revalidate instead of refetching."""
    client.force_login(alice)

    response = client.get(
        stream_url(video),
        headers={'if-modified-since': http_date(video.file_path.stat().st_mtime)},
    )

    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.content == b''


def test_conditional_request_of_another_users_file_is_not_answered(client, bob, video):
    """The ownership check runs first, so a 304 cannot confirm the file's age."""
    client.force_login(bob)

    response = client.get(
        stream_url(video),
        headers={'if-modified-since': http_date(video.file_path.stat().st_mtime)},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
