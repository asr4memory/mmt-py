from http import HTTPStatus
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from mmt.projects.models import ProcessingRequest
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

PERMISSION_CODENAMES = (
    'view_uploadedfile',
    'add_uploadedfile',
    'view_processingrequest',
    'add_processingrequest',
    'delete_processingrequest',
)

TABS = ('uploaded-files', 'downloads', 'processing-requests', 'settings')


def tab_url(project, tab: str) -> str:
    """The URL of one tab of a project."""
    paths = {
        'uploaded-files': '',
        'downloads': 'downloads/',
        'processing-requests': 'processing-requests/',
        'settings': 'settings/',
    }
    return f'/projects/{project.pk}/{paths[tab]}'


def make_user(username: str, *, permissions=PERMISSION_CODENAMES):
    user = User.objects.create_user(
        username=username,
        password='password',
        email=f'{username}@example.com',
        terms_accepted_version=1,
    )
    for codename in permissions:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


@pytest.fixture
def alice(db):
    return make_user('alice')


@pytest.fixture
def bob(db):
    return make_user('bob')


@pytest.fixture
def empty_project(alice):
    """A project without uploaded files and without processing requests."""
    return create_project(title='Empty project', user=alice)


@pytest.fixture
def project(alice):
    """A project with one uploaded file and one processing request."""
    project = create_project(title='Test project', user=alice)
    UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    ProcessingRequest.objects.create(
        project=project,
        description='Put on platform.',
        make_available_on_platform=True,
    )
    return project


@pytest.fixture
def alice_client(client, alice):
    client.force_login(alice)
    return client


def soup_of(response) -> BeautifulSoup:
    return BeautifulSoup(response.content, 'html.parser')


def find_tab(soup, tab: str):
    return soup.find(attrs={'data-testid': f'{tab}-tab'})


#
# Routing and the tab bar
#
def test_detail_page_shows_four_tabs(alice_client, project):
    """The detail page has a link for each of the four tabs."""
    response = alice_client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    for tab in TABS:
        link = find_tab(soup, tab)
        assert link is not None, f'missing tab link {tab}'
        assert link['href'] == tab_url(project, tab)


def test_tab_links_have_href_and_hx_get(alice_client, project):
    """Each tab link carries an href and an hx-get with the same URL."""
    response = alice_client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    for tab in TABS:
        link = find_tab(soup, tab)
        assert link['href'] == tab_url(project, tab)
        assert link['hx-get'] == tab_url(project, tab)


def test_detail_page_marks_uploaded_files_tab_active(alice_client, project):
    """On the detail page only the uploaded files tab is the current page."""
    response = alice_client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    assert find_tab(soup, 'uploaded-files').get('aria-current') == 'page'
    for tab in ('downloads', 'processing-requests', 'settings'):
        assert find_tab(soup, tab).get('aria-current') is None


def test_downloads_page_marks_downloads_tab_active(alice_client, project):
    """On the downloads page only the downloads tab is the current page."""
    response = alice_client.get(tab_url(project, 'downloads'))
    soup = soup_of(response)

    assert find_tab(soup, 'downloads').get('aria-current') == 'page'
    for tab in ('uploaded-files', 'processing-requests', 'settings'):
        assert find_tab(soup, tab).get('aria-current') is None


def test_processing_requests_tab_hidden_without_uploaded_files_or_requests(
    alice_client, empty_project
):
    """A project with neither uploaded files nor requests has no requests tab."""
    response = alice_client.get(tab_url(empty_project, 'uploaded-files'))
    soup = soup_of(response)

    assert find_tab(soup, 'processing-requests') is None


def test_processing_requests_tab_hidden_without_view_permission(client, project):
    """A user without view_processingrequest has no requests tab."""
    project.user.user_permissions.clear()
    client.force_login(project.user)

    response = client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    assert find_tab(soup, 'processing-requests') is None


def test_settings_tab_replaces_settings_button(alice_client, project):
    """The settings link in the page header is gone; the tab replaces it."""
    response = alice_client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    settings_url = tab_url(project, 'settings')
    buttons = [
        link
        for link in soup.find_all('a', class_='button-link')
        if link.get('href') == settings_url
    ]
    assert buttons == []


#
# Panel content
#
def test_uploaded_files_tab_shows_only_its_panel(alice_client, project):
    """The detail page renders the uploaded files panel and no other panel."""
    response = alice_client.get(tab_url(project, 'uploaded-files'))
    soup = soup_of(response)

    assert soup.find(attrs={'data-testid': 'uploaded-files-count'}) is not None
    assert soup.find(attrs={'data-testid': 'downloadable-files-count'}) is None
    assert soup.find(attrs={'data-testid': 'processing-request-card'}) is None


def test_downloads_tab_shows_downloads_panel(alice_client, project):
    """The downloads page renders the downloads panel and not the files panel."""
    response = alice_client.get(tab_url(project, 'downloads'))
    soup = soup_of(response)

    assert soup.find(attrs={'data-testid': 'downloadable-files-count'}) is not None
    assert soup.find(attrs={'data-testid': 'uploaded-files-count'}) is None


def test_processing_requests_tab_shows_requests_panel(alice_client, project):
    """The processing requests page renders the project's requests."""
    response = alice_client.get(tab_url(project, 'processing-requests'))
    soup = soup_of(response)

    assert soup.find(attrs={'data-testid': 'processing-request-card'}) is not None


def test_settings_tab_shows_edit_form(alice_client, project):
    """The settings page renders the edit form and the delete button."""
    response = alice_client.get(tab_url(project, 'settings'))
    soup = soup_of(response)

    assert soup.find(attrs={'data-testid': 'edit-project-form'}) is not None
    assert soup.find(attrs={'data-testid': 'delete-project-button'}) is not None


def test_processing_requests_tab_renders_when_section_condition_is_false(
    alice_client, empty_project
):
    """The tab is reachable by URL even when it is not shown in the tab bar."""
    response = alice_client.get(tab_url(empty_project, 'processing-requests'))

    assert response.status_code == HTTPStatus.OK
    assert 'You haven’t submitted any processing requests yet.' in response.content.decode()


def test_processing_requests_tab_without_view_permission_returns_403(client, project):
    """Missing view_processingrequest is refused, not redirected."""
    project.user.user_permissions.clear()
    client.force_login(project.user)

    response = client.get(tab_url(project, 'processing-requests'))

    assert response.status_code == HTTPStatus.FORBIDDEN


#
# Panel snippets
#
def test_htmx_request_returns_panel_without_layout(alice_client, project):
    """An htmx request returns only the panel, without the layout or tab bar."""
    response = alice_client.get(
        tab_url(project, 'downloads'), headers={'hx-request': 'true'}
    )

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert 'downloadable-files-count' in body
    assert '<html' not in body
    assert 'downloads-tab' not in body


def test_htmx_request_varies_on_hx_request(alice_client, project):
    """The response varies on HX-Request so a cache cannot mix up the two forms."""
    response = alice_client.get(
        tab_url(project, 'downloads'), headers={'hx-request': 'true'}
    )

    assert 'HX-Request' in response.headers['Vary']


def test_full_request_returns_whole_page(alice_client, project):
    """The same URL without the header returns the whole page."""
    response = alice_client.get(tab_url(project, 'downloads'))

    body = response.content.decode()
    assert '<html' in body
    assert 'downloads-tab' in body


@pytest.mark.parametrize(
    ('tab', 'marker'),
    [
        ('uploaded-files', 'uploaded-files-count'),
        ('downloads', 'downloadable-files-count'),
        ('processing-requests', 'processing-request-card'),
        ('settings', 'edit-project-form'),
    ],
)
def test_htmx_request_for_each_tab(alice_client, project, tab, marker):
    """Every tab answers an htmx request with its own panel."""
    response = alice_client.get(tab_url(project, tab), headers={'hx-request': 'true'})

    assert response.status_code == HTTPStatus.OK
    assert marker in response.content.decode()


#
# Ownership and downloads
#
@pytest.mark.parametrize('tab', TABS)
def test_each_tab_returns_404_for_another_users_project(client, bob, project, tab):
    """No tab of a project is visible to another user."""
    client.force_login(bob)

    response = client.get(tab_url(project, tab))

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize('tab', TABS)
def test_each_tab_redirects_anonymous_to_login(client, project, tab):
    """Every tab requires a signed-in user."""
    url = tab_url(project, tab)

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f'/accounts/login/?next={url}'


def test_downloads_tab_missing_directory_returns_500(alice_client, project):
    """A missing download directory renders the error page on the downloads tab."""
    with mock.patch(
        'mmt.projects.views.get_files_with_info', side_effect=FileNotFoundError
    ):
        response = alice_client.get(tab_url(project, 'downloads'))

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert 'projects/project_detail_error.html' in [
        template.name for template in response.templates
    ]


def test_detail_page_missing_download_directory_still_returns_200(
    alice_client, project
):
    """The uploaded files tab does not read the download directory."""
    with mock.patch(
        'mmt.projects.views.get_files_with_info', side_effect=FileNotFoundError
    ):
        response = alice_client.get(tab_url(project, 'uploaded-files'))

    assert response.status_code == HTTPStatus.OK


def test_downloads_tab_updates_downloadable_files_count(alice_client, project):
    """Opening the downloads tab writes the stored count."""
    (project.download_directory / 'result.txt').write_text('done')

    alice_client.get(tab_url(project, 'downloads'))

    project.refresh_from_db()
    assert project.downloadable_files_count == 1
