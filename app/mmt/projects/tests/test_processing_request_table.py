import datetime

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.models import ProcessingRequest
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def user(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(
        Permission.objects.get(codename='view_processingrequest'),
        Permission.objects.get(codename='add_processingrequest'),
    )
    return user


@pytest.fixture
def project(user):
    project = create_project(title='Test project', user=user)
    UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    return project


def add_processing_request(project, **kwargs):
    fields = {
        'make_available_on_platform': True,
        'replace_existing_files': False,
        'transcribe': False,
        'check_media_files': False,
    }
    fields.update(kwargs)
    return ProcessingRequest.objects.create(project=project, **fields)


def set_timestamps(processing_request, created_at, updated_at):
    ProcessingRequest.objects.filter(pk=processing_request.pk).update(
        created_at=created_at, updated_at=updated_at
    )


def rows(response):
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.find_all(attrs={'data-testid': 'processing-request-row'})


def test_row_links_to_the_processing_request_detail_page(client, user, project):
    processing_request = add_processing_request(project)
    client.force_login(user)

    response = client.get(f'/projects/{project.id}/')

    link = rows(response)[0].find('a')
    assert link['href'] == (
        f'/projects/{project.id}/processing-requests/{processing_request.id}/'
    )


def test_row_shows_the_fields_of_the_processing_request(client, user, project):
    processing_request = add_processing_request(
        project,
        status=ProcessingRequest.Status.COMPLETED,
        language='de',
        uploaded_files=['first.mp4', 'second.mp4'],
        make_available_on_platform=True,
        replace_existing_files=False,
        transcribe=True,
        check_media_files=False,
    )
    set_timestamps(
        processing_request,
        datetime.datetime(2026, 1, 5, 9, 0, tzinfo=datetime.UTC),
        datetime.datetime(2026, 2, 17, 14, 30, tzinfo=datetime.UTC),
    )
    client.force_login(user)

    response = client.get(f'/projects/{project.id}/')

    row = rows(response)[0]
    times = row.find_all('time')
    assert times[0]['datetime'].startswith('2026-01-05')
    assert times[1]['datetime'].startswith('2026-02-17')
    cells = [cell.get_text(strip=True) for cell in row.find_all('td')]
    assert cells[2:] == ['Completed', '2', 'German', '✔', '✘', '✔', '✘']
