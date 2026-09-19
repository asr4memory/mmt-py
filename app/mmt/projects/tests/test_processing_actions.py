"""The processing actions are derived from a single registry.

Every test here iterates over ``ACTIONS`` instead of naming the individual
fields, so a new action is covered by the existing tests as soon as it is
added to the registry.
"""

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError

from mmt.projects.forms import ProcessingRequestForm
from mmt.projects.models import ACTIONS, ProcessingRequest
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
def superuser_client(client, db):
    superuser = User.objects.create_superuser(
        username='admin',
        password='password',
        email='admin@example.com',
        terms_accepted_version=1,
    )
    client.force_login(superuser)
    return client


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
    fields = {action.field: False for action in ACTIONS}
    fields[ACTIONS[0].field] = True
    fields.update(kwargs)
    return ProcessingRequest.objects.create(project=project, **fields)


def indicator(value):
    return '✔' if value else '✘'


def test_the_form_has_one_field_per_action_in_registry_order(project):
    form = ProcessingRequestForm(instance=ProcessingRequest(project=project))

    assert [field.name for field in form.action_fields] == [
        action.field for action in ACTIONS
    ]


def test_the_create_page_renders_a_labelled_checkbox_per_action(client, user, project):
    client.force_login(user)

    response = client.get(f'/projects/{project.id}/processing-requests/create/')

    soup = BeautifulSoup(response.content, 'html.parser')
    for action in ACTIONS:
        checkbox = soup.find('input', attrs={'name': action.field})
        assert checkbox is not None, f'no checkbox for {action.field}'
        assert checkbox['type'] == 'checkbox'
        label = soup.find('label', attrs={'for': checkbox['id']})
        assert label.get_text(strip=True) == str(action.label)


def test_the_table_has_a_column_per_action_in_registry_order(client, user, project):
    add_processing_request(project)
    client.force_login(user)

    response = client.get(f'/projects/{project.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    row = soup.find(attrs={'data-testid': 'processing-request-row'})
    headers = row.find_parent('table').find_all('th')[-len(ACTIONS) :]
    assert [header.get_text(strip=True) for header in headers] == [
        str(action.column) for action in ACTIONS
    ]
    assert [header['title'] for header in headers] == [
        str(action.label) for action in ACTIONS
    ]


def test_the_table_shows_the_value_of_every_action(client, user, project):
    processing_request = add_processing_request(project, transcribe=True)
    client.force_login(user)

    response = client.get(f'/projects/{project.id}/')

    soup = BeautifulSoup(response.content, 'html.parser')
    row = soup.find(attrs={'data-testid': 'processing-request-row'})
    cells = row.find_all('td')[-len(ACTIONS) :]
    assert [cell.get_text(strip=True) for cell in cells] == [
        indicator(getattr(processing_request, action.field)) for action in ACTIONS
    ]


def test_the_detail_page_shows_every_action(client, user, project):
    processing_request = add_processing_request(project, transcribe=True)
    client.force_login(user)

    response = client.get(
        f'/projects/{project.id}/processing-requests/{processing_request.id}/'
    )

    soup = BeautifulSoup(response.content, 'html.parser')
    values = {
        term.get_text(strip=True): term.find_next_sibling('dd').get_text(strip=True)
        for term in soup.find_all('dt')
    }
    for action in ACTIONS:
        assert values[str(action.label)] == indicator(
            getattr(processing_request, action.field)
        )


def test_the_admin_shows_every_action(superuser_client, project):
    # The change page renders uploaded_files_list, which raises on an empty
    # list, so the request needs a file.
    processing_request = add_processing_request(
        project, uploaded_files=['test_file.mp4']
    )

    response = superuser_client.get(
        f'/admin/projects/processingrequest/{processing_request.id}/change/'
    )

    content = response.content.decode()
    for action in ACTIONS:
        assert str(action.label) in content


@pytest.mark.parametrize('action', ACTIONS, ids=[action.field for action in ACTIONS])
def test_a_request_with_a_single_action_is_accepted(project, action):
    processing_request = ProcessingRequest.objects.create(
        project=project, **{action.field: True}
    )

    assert getattr(processing_request, action.field) is True


def test_a_request_without_any_action_is_rejected(project):
    with pytest.raises(IntegrityError):
        ProcessingRequest.objects.create(project=project)
