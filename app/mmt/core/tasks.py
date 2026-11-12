from celery import shared_task
from silk.models import Request


@shared_task
def add(x, y):
    return x + y


@shared_task
def task_delete_old_silk_requests() -> None:
    """Delete the silk requests beyond SILKY_MAX_RECORDED_REQUESTS, oldest first."""
    # Same call as silk's silk_request_garbage_collect management command.
    Request.garbage_collect(force=True)
