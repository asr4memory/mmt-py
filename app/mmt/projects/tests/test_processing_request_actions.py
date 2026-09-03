from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from mmt.projects.models import ProcessingRequest
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def alice(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(
        *Permission.objects.filter(
            codename__in=['view_processingrequest', 'add_processingrequest']
        )
    )
    return user


@pytest.fixture
def project(alice):
    project = create_project(title='Test project', user=alice)
    UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    return project


@pytest.fixture
def create_url(project):
    return reverse('projects:create-processing-request', args=[project.id])


@pytest.mark.parametrize('action', ['make_available_on_avd', 'align_transcripts'])
def test_a_request_with_only_the_new_action_is_created(
    client, alice, project, create_url, action
):
    client.force_login(alice)

    with mock.patch('mmt.projects.tasks.send_new_processing_request_email.delay'):
        response = client.post(
            create_url,
            {
                'description': 'Please do this.',
                'uploaded_files': ['test_file.mp4'],
                action: True,
                'language': 'de',
            },
        )

    assert response.status_code == 302
    processing_request = ProcessingRequest.objects.get()
    assert getattr(processing_request, action) is True


def test_the_create_form_offers_the_new_actions(client, alice, create_url):
    client.force_login(alice)

    response = client.get(create_url)

    content = response.content.decode()
    assert 'Make media files available on Audio-Visual.Digital' in content
    assert 'Align existing transcripts with media files' in content


def test_the_detail_page_shows_the_new_actions(client, alice, project):
    processing_request = ProcessingRequest.objects.create(
        project=project, make_available_on_avd=True, align_transcripts=True
    )
    client.force_login(alice)

    response = client.get(
        reverse('projects:processing-request', args=[project.id, processing_request.id])
    )

    content = response.content.decode()
    assert 'Make media files available on Audio-Visual.Digital' in content
    assert 'Align existing transcripts with media files' in content
