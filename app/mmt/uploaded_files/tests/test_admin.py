import pytest
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        project=project,
        filename='rt.mp4',
        original_filename='რთ.mp4',
        size=20000,
        media_type='video/mp4',
    )


@pytest.fixture
def superuser_client(client, db):
    superuser = User.objects.create_superuser(
        username='admin',
        password='password',
        email='admin@example.com',
        terms_accepted_version=1,
    )
    client.force_login(superuser)
    return client


def test_changelist_shows_both_names(superuser_client, uploaded_file):
    """The administrator matches a file on disk against the name a user reported."""
    response = superuser_client.get('/admin/uploaded_files/uploadedfile/')

    content = response.content.decode()
    assert 'rt.mp4' in content
    assert 'რთ.mp4' in content


def test_project_inline_shows_both_names(superuser_client, uploaded_file):
    """The inline on the project page mirrors the changelist columns."""
    response = superuser_client.get(
        f'/admin/projects/project/{uploaded_file.project_id}/change/'
    )

    content = response.content.decode()
    assert 'rt.mp4' in content
    assert 'რთ.mp4' in content


def test_changelist_finds_a_row_by_either_name(superuser_client, uploaded_file):
    for term in ['rt.mp4', 'რთ.mp4']:
        response = superuser_client.get(
            '/admin/uploaded_files/uploadedfile/', {'q': term}
        )

        assert str(uploaded_file.pk) in response.content.decode()
