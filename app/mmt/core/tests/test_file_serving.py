"""Tests for both paths of `serve_file`: direct streaming and delegation."""

import pytest
from django.core.exceptions import SuspiciousFileOperation
from django.test import RequestFactory

from mmt.core.file_serving import serve_file

LOCATION = '/internal-media/'


@pytest.fixture
def user_files(settings, tmp_path):
    """An empty user files directory that `serve_file` treats as its root."""
    settings.MMT_USER_FILES_DIR = tmp_path
    return tmp_path


@pytest.fixture
def media_file(user_files):
    """A file inside the user files directory, in a project-like subdirectory."""
    path = user_files / 'alice' / 'project' / 'upload' / 'recording.mp4'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'0123456789')
    return path


@pytest.fixture
def request_factory():
    return RequestFactory()


def test_serves_the_file_itself_when_the_setting_is_empty(
    settings, request_factory, media_file
):
    """An empty setting keeps the existing streaming implementation."""
    settings.MMT_X_ACCEL_LOCATION = ''
    request = request_factory.get('/')

    response = serve_file(request, media_file, content_type='video/mp4')

    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'0123456789'
    assert 'X-Accel-Redirect' not in response


def test_delegates_to_nginx_when_the_setting_is_set(
    settings, request_factory, media_file
):
    """The response names the file below the configured internal location."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/')

    response = serve_file(request, media_file, content_type='video/mp4')

    assert response.status_code == 200
    assert (
        response['X-Accel-Redirect']
        == '/internal-media/alice/project/upload/recording.mp4'
    )
    assert response['Content-Type'] == 'video/mp4'


def test_the_delegated_response_has_an_empty_body_and_no_content_length(
    settings, request_factory, media_file
):
    """nginx determines the length, so Django must not claim one."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/')

    response = serve_file(request, media_file, content_type='video/mp4')

    assert response.content == b''
    assert 'Content-Length' not in response


def test_the_delegated_response_sets_no_range_headers(
    settings, request_factory, media_file
):
    """`Accept-Ranges` and `Content-Range` are nginx's to send."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/')

    response = serve_file(request, media_file, content_type='video/mp4')

    assert 'Accept-Ranges' not in response
    assert 'Content-Range' not in response


def test_a_range_header_is_ignored_on_the_delegated_path(
    settings, request_factory, media_file
):
    """nginx applies the range to the internal request itself."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/', headers={'range': 'bytes=2-5'})

    response = serve_file(request, media_file, content_type='video/mp4')

    assert response.status_code == 200
    assert response.content == b''
    assert 'Content-Range' not in response


def test_a_non_ascii_path_is_percent_encoded(settings, request_factory, user_files):
    """Names predating the ASCII filenames feature can hold any character."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    path = user_files / 'alice' / 'რთ ვიდეო.mp4'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'0123456789')
    request = request_factory.get('/')

    response = serve_file(request, path, content_type='video/mp4')

    assert response['X-Accel-Redirect'] == (
        '/internal-media/alice/'
        '%E1%83%A0%E1%83%97%20%E1%83%95%E1%83%98%E1%83%93%E1%83%94%E1%83%9D.mp4'
    )


def test_the_delegated_response_is_inline_by_default(
    settings, request_factory, media_file
):
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/')

    response = serve_file(request, media_file, content_type='video/mp4')

    assert response['Content-Disposition'] == 'inline'


def test_the_delegated_attachment_name_is_rfc_8187_encoded(
    settings, request_factory, media_file
):
    """The disposition is built exactly as the direct path builds it."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    request = request_factory.get('/')

    response = serve_file(
        request,
        media_file,
        content_type='application/octet-stream',
        as_attachment=True,
        filename='რთ.mp4',
    )

    assert (
        response['Content-Disposition']
        == "attachment; filename*=utf-8''%E1%83%A0%E1%83%97.mp4"
    )


def test_a_symlinked_user_files_directory_still_resolves(
    settings, request_factory, tmp_path
):
    """A symlinked user files directory is normal in development."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real)
    settings.MMT_USER_FILES_DIR = link
    path = real / 'recording.mp4'
    path.write_bytes(b'0123456789')
    request = request_factory.get('/')

    response = serve_file(request, path, content_type='video/mp4')

    assert response['X-Accel-Redirect'] == '/internal-media/recording.mp4'


def test_a_path_outside_the_user_files_directory_is_refused(
    settings, request_factory, user_files, tmp_path
):
    """Delegating a path nginx cannot see is a programming error."""
    settings.MMT_X_ACCEL_LOCATION = LOCATION
    settings.MMT_USER_FILES_DIR = user_files / 'inner'
    (user_files / 'inner').mkdir()
    outside = tmp_path / 'outside.mp4'
    outside.write_bytes(b'0123456789')
    request = request_factory.get('/')

    with pytest.raises(SuspiciousFileOperation):
        serve_file(request, outside, content_type='video/mp4')
