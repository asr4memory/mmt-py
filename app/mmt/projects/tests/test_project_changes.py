import shutil
from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model

from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.use_cases import create_project

User = get_user_model()

PAST = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )


@pytest.fixture
def project(user):
    """A project whose updated_at lies in the past."""
    project = create_project(title='Test project', user=user)
    Project.objects.filter(pk=project.pk).update(updated_at=PAST)
    project.refresh_from_db()
    yield project
    shutil.rmtree(project.project_directory, ignore_errors=True)


def stored_updated_at(project):
    return Project.objects.values_list('updated_at', flat=True).get(pk=project.pk)


def test_mark_changed_sets_updated_at(project):
    project.mark_changed()

    assert stored_updated_at(project) > PAST
    assert project.updated_at == stored_updated_at(project)


def test_mark_changed_keeps_a_concurrent_title_change(project):
    other = Project.objects.get(pk=project.pk)
    other.title = 'Changed elsewhere'
    other.save()

    project.mark_changed()

    project.refresh_from_db()
    assert project.title == 'Changed elsewhere'


def test_detail_page_stores_the_count_without_marking_the_project_changed(
    client, user, project
):
    (project.download_directory / 'result.zip').write_bytes(b'data')
    assert project.downloadable_files_count == 0
    client.force_login(user)

    response = client.get(f'/projects/{project.pk}/')

    assert response.status_code == 200
    project.refresh_from_db()
    assert project.downloadable_files_count == 1
    assert project.updated_at == PAST


def test_deleting_a_downloadable_file_marks_the_project_changed(
    client, user, project, marks_project_changed
):
    (project.download_directory / 'result.zip').write_bytes(b'data')
    client.force_login(user)

    with marks_project_changed(project):
        response = client.post(f'/projects/{project.pk}/downloads/result.zip/')

    assert response.status_code == 302


def test_creating_a_processing_request_marks_the_project_changed(
    project, marks_project_changed
):
    with marks_project_changed(project):
        ProcessingRequest.objects.create(project=project, transcribe=True)


def test_deleting_a_processing_request_marks_the_project_changed(
    project, marks_project_changed
):
    processing_request = ProcessingRequest.objects.create(
        project=project, transcribe=True
    )

    with marks_project_changed(project):
        processing_request.delete()
