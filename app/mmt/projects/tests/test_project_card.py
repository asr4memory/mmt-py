import datetime

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model

from mmt.projects.models import Project
from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
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


def add_uploaded_file(project, filename, has_file=True):
    return UploadedFile.objects.create(
        project=project,
        filename=filename,
        original_filename=filename,
        has_file=has_file,
        size=20000,
        media_type='video/mp4',
    )


def add_transcript(uploaded_file):
    return Transcript.objects.create(uploaded_file=uploaded_file, label='Label')


def cards(client, user):
    client.force_login(user)
    response = client.get('/projects/')
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.find_all(attrs={'data-testid': 'project-card'})


def summary(card):
    element = card.find(attrs={'data-testid': 'project-card-summary'})
    return ' '.join(element.get_text().split())


def test_summary_without_files(client, user):
    create_project(title='Project', user=user)

    assert summary(cards(client, user)[0]) == 'No files yet'


def test_summary_with_incomplete_file(client, user):
    project = create_project(title='Project', user=user)
    add_uploaded_file(project, 'first.mp4')
    add_uploaded_file(project, 'second.mp4')
    add_uploaded_file(project, 'third.mp4', has_file=False)

    assert summary(cards(client, user)[0]) == '2 files (+1)'


def test_summary_with_incomplete_file_only(client, user):
    project = create_project(title='Project', user=user)
    add_uploaded_file(project, 'first.mp4', has_file=False)

    assert summary(cards(client, user)[0]) == '0 files (+1)'


def test_summary_with_transcript(client, user):
    project = create_project(title='Project', user=user)
    add_transcript(add_uploaded_file(project, 'first.mp4'))
    add_uploaded_file(project, 'second.mp4')

    assert summary(cards(client, user)[0]) == '2 files · 1 transcript'


def test_summary_counts_files_and_transcripts_distinctly(client, user):
    project = create_project(title='Project', user=user)
    uploaded_file = add_uploaded_file(project, 'first.mp4')
    add_transcript(uploaded_file)
    add_transcript(uploaded_file)
    add_uploaded_file(project, 'second.mp4')

    assert summary(cards(client, user)[0]) == '2 files · 2 transcripts'


def test_card_time_is_updated_at(client, user):
    project = create_project(title='Project', user=user)
    created_at = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
    updated_at = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=datetime.UTC)
    Project.objects.filter(pk=project.pk).update(
        created_at=created_at, updated_at=updated_at
    )

    time = cards(client, user)[0].find('time')

    assert datetime.datetime.fromisoformat(time['datetime']) == updated_at


def test_cards_are_ordered_by_updated_at(client, user):
    first = create_project(title='First', user=user)
    second = create_project(title='Second', user=user)
    Project.objects.filter(pk=first.pk).update(
        created_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
    )
    Project.objects.filter(pk=second.pk).update(
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC),
    )

    titles = [card.find('h3').get_text() for card in cards(client, user)]

    assert titles == ['Second', 'First']
