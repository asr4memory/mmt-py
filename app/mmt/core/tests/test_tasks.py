from datetime import timedelta

import pytest
from django.utils import timezone
from silk.config import SilkyConfig
from silk.models import Request

from mmt.core.tasks import add, task_delete_old_silk_requests


def test_add_direct():
    assert add(2, 3) == 5


@pytest.mark.django_db
def test_delete_old_silk_requests_deletes_down_to_the_limit(monkeypatch):
    # Production sets the check percent to 0. The task has to delete anyway.
    monkeypatch.setitem(
        SilkyConfig().attrs, 'SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT', 0
    )
    monkeypatch.setitem(SilkyConfig().attrs, 'SILKY_MAX_RECORDED_REQUESTS', 2)
    now = timezone.now()
    for age in range(5):
        Request.objects.create(
            path='/', method='GET', start_time=now - timedelta(minutes=age)
        )

    task_delete_old_silk_requests()

    assert Request.objects.count() == 2
