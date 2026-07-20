from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileChunk, UploadedFile

User = get_user_model()

CHUNK_SIZE = settings.MMT_UPLOAD_CHUNK_SIZE


@pytest.fixture
def alice(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(Permission.objects.get(codename='add_uploadedfile'))
    return user


@pytest.fixture
def project(alice):
    return create_project(title='Test project', user=alice)


@pytest.fixture
def alice_client(client, alice):
    client.force_login(alice)
    return client


def lookup(client, project, files):
    return client.post(
        f'/projects/{project.id}/resumable-uploads/',
        {'files': files},
        content_type='application/json',
    )


def make_incomplete(project, *, filename, size, received_indices, checksum_client=''):
    # The stored filename is unique per project (see the unique_filename
    # constraint); the original filename is what the lookup matches on, so
    # several incomplete uploads of the same file share it.
    count = project.uploaded_files.count()
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename=f'{count}-{filename}',
        original_filename=filename,
        size=size,
        checksum_client=checksum_client,
    )
    for index in received_indices:
        FileChunk.objects.create(uploaded_file=uploaded_file, index=index)
    return uploaded_file


def test_incomplete_match_returns_missing_chunks(alice_client, project):
    uploaded_file = make_incomplete(
        project, filename='clip.mp4', size=3 * CHUNK_SIZE, received_indices=[0]
    )

    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'matches': [
            {
                'filename': 'clip.mp4',
                'size': 3 * CHUNK_SIZE,
                'id': uploaded_file.id,
                'chunks_missing': [1, 2],
                'checksum_submitted': False,
            }
        ],
    }


def test_checksum_submitted_is_true_when_client_checksum_stored(
    alice_client, project
):
    make_incomplete(
        project,
        filename='clip.mp4',
        size=3 * CHUNK_SIZE,
        received_indices=[0],
        checksum_client='abc123',
    )

    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.json()['matches'][0]['checksum_submitted'] is True


def test_no_incomplete_file_is_omitted(alice_client, project):
    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'matches': []}


def test_complete_file_is_not_matched(alice_client, project):
    UploadedFile.objects.create(
        project=project,
        filename='clip.mp4',
        original_filename='clip.mp4',
        size=3 * CHUNK_SIZE,
        has_file=True,
    )

    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.json() == {'matches': []}


def test_size_mismatch_is_not_matched(alice_client, project):
    make_incomplete(
        project, filename='clip.mp4', size=3 * CHUNK_SIZE, received_indices=[0]
    )

    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 5 * CHUNK_SIZE}]
    )

    assert response.json() == {'matches': []}


def test_another_users_project_is_not_accessible(client, project):
    bob = User.objects.create_user(
        username='bob',
        password='password',
        email='bob@example.com',
        terms_accepted_version=1,
    )
    bob.user_permissions.add(Permission.objects.get(codename='add_uploadedfile'))
    client.force_login(bob)

    response = lookup(
        client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_multiple_matches_returns_newest(alice_client, project):
    make_incomplete(
        project, filename='clip.mp4', size=3 * CHUNK_SIZE, received_indices=[0]
    )
    newer = make_incomplete(
        project, filename='clip.mp4', size=3 * CHUNK_SIZE, received_indices=[0, 1]
    )

    response = lookup(
        alice_client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    matches = response.json()['matches']
    assert len(matches) == 1
    assert matches[0]['id'] == newer.id
    assert matches[0]['chunks_missing'] == [2]


def test_invalid_json_returns_400(alice_client, project):
    response = alice_client.post(
        f'/projects/{project.id}/resumable-uploads/',
        'not json',
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'message': 'Invalid JSON'}


def test_missing_permission_returns_403(client, project):
    charlie = User.objects.create_user(
        username='charlie',
        password='password',
        email='charlie@example.com',
        terms_accepted_version=1,
    )
    client.force_login(charlie)

    response = lookup(
        client, project, [{'filename': 'clip.mp4', 'size': 3 * CHUNK_SIZE}]
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
