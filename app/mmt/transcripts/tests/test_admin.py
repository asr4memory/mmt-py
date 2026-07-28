from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


@pytest.fixture
def transcript(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='test_file.mp4',
        original_filename='test_file.mp4',
        has_file=True,
        size=20000,
        media_type='video/mp4',
    )
    return Transcript.objects.create(
        label='Test transcript',
        content={'format': 'mmt-transcript', 'version': 1, 'segments': []},
        uploaded_file=uploaded_file,
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


def transcript_queries(captured_queries):
    return [
        query['sql']
        for query in captured_queries
        if 'transcripts_transcript' in query['sql']
    ]


def test_changelist_does_not_select_content(superuser_client, transcript):
    """The changelist shows label and created_at, so content stays unloaded."""
    with CaptureQueriesContext(connection) as context:
        response = superuser_client.get('/admin/transcripts/transcript/')

    assert response.status_code == HTTPStatus.OK
    queries = transcript_queries(context.captured_queries)
    content_column = connection.ops.quote_name('content')
    assert queries
    assert not any(content_column in sql for sql in queries)


def test_change_form_shows_content(superuser_client, transcript):
    """The change form loads content even though the queryset defers it."""
    response = superuser_client.get(
        f'/admin/transcripts/transcript/{transcript.pk}/change/'
    )

    assert response.status_code == HTTPStatus.OK
    assert 'mmt-transcript' in response.content.decode()
