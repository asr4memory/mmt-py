import base64
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest


@pytest.fixture
def png_bytes():
    """A 1x1 pixel PNG image, for tests that need contents libmagic recognises."""
    return base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
        '60e6kgAAAABJRU5ErkJggg=='
    )


@pytest.fixture
def marks_project_changed(db):
    """A context manager that asserts that its block marks the project changed.

    Before the block it sets updated_at of the project to a past day; after the
    block it asserts that the stored value is later than that day.
    """
    # Imported here, because Django is not set up when pytest imports this file.
    from mmt.projects.models import Project

    past = datetime(2020, 1, 1, tzinfo=UTC)

    @contextmanager
    def check(project):
        Project.objects.filter(pk=project.pk).update(updated_at=past)
        yield
        stored = Project.objects.values_list('updated_at', flat=True).get(pk=project.pk)
        assert stored > past

    return check
