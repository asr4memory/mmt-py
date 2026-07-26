import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )


def add_uploaded_file(project, filename):
    return UploadedFile.objects.create(
        project=project,
        filename=filename,
        original_filename=filename,
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )


def card_texts(response):
    soup = BeautifulSoup(response.content, 'html.parser')
    cards = soup.find_all(attrs={'data-testid': 'project-card'})
    return [card.get_text() for card in cards]


def test_card_shows_the_number_of_uploaded_files(client, user):
    project = create_project(title='Test project', user=user)
    add_uploaded_file(project, 'first.mp4')
    add_uploaded_file(project, 'second.mp4')
    client.force_login(user)

    response = client.get('/projects/')

    assert '2 uploads' in card_texts(response)[0]


def test_card_shows_zero_uploaded_files(client, user):
    create_project(title='Empty project', user=user)
    client.force_login(user)

    response = client.get('/projects/')

    assert '0 uploads' in card_texts(response)[0]
