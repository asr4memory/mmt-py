import os

from celery import Celery

from extraction import extract

app = Celery("ner")
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    # A job whose worker stops during inference stays in the broker and is
    # delivered again.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


@app.task(
    name="ner.extract",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def extract_entities(batches: list[list[str]]) -> list[list[dict]]:
    """Extract entity spans from word batches."""
    return extract(batches)
