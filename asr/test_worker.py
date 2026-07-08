import json
import time

import pytest

import jobs
from worker import Worker


@pytest.fixture
def media_root(tmp_path, monkeypatch):
    root = tmp_path / "media"
    root.mkdir()
    (root / "interview.mp4").write_bytes(b"fake media")
    monkeypatch.setenv("MEDIA_ROOT", str(root))
    return root


@pytest.fixture
def spool(tmp_path):
    return tmp_path / "spool"


def fake_transcribe(media, language, diarize, progress):
    return {"language": language or "en", "segments": [{"start": 0.0, "text": "hi"}]}


def make_worker(spool, transcribe=fake_transcribe):
    return Worker(spool, transcribe)


def test_run_once_without_a_queued_job_does_nothing(spool, media_root):
    spool.mkdir()

    assert make_worker(spool).run_once() is False


def test_a_queued_job_succeeds_and_writes_its_result(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", "de", False)

    assert make_worker(spool).run_once() is True

    finished = jobs.load_job(spool, job["id"])
    assert finished["status"] == "succeeded"
    assert finished["progress"] == 1.0
    assert finished["error"] is None
    assert finished["started_at"] is not None
    assert finished["finished_at"] is not None
    result = json.loads(jobs.result_path(spool, job["id"]).read_text())
    assert result == {"language": "de", "segments": [{"start": 0.0, "text": "hi"}]}


def test_the_running_job_is_marked_running_and_gets_the_media_path(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, True)
    seen = {}

    def transcribe(media, language, diarize, progress):
        seen["media"] = media
        seen["language"] = language
        seen["diarize"] = diarize
        seen["status"] = jobs.load_job(spool, job["id"])["status"]
        return {"segments": []}

    make_worker(spool, transcribe).run_once()

    assert seen["media"] == media_root / "interview.mp4"
    assert seen["language"] is None
    assert seen["diarize"] is True
    assert seen["status"] == "running"


def test_progress_callback_lands_in_the_job_file(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, False)

    def transcribe(media, language, diarize, progress):
        progress(0.35)
        assert jobs.load_job(spool, job["id"])["progress"] == pytest.approx(0.35)
        progress(0.7)
        return {"segments": []}

    make_worker(spool, transcribe).run_once()

    assert jobs.load_job(spool, job["id"])["progress"] == 1.0


def test_a_failing_transcriber_marks_the_job_failed(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, False)

    def transcribe(media, language, diarize, progress):
        raise RuntimeError("CUDA out of memory")

    make_worker(spool, transcribe).run_once()

    failed = jobs.load_job(spool, job["id"])
    assert failed["status"] == "failed"
    assert failed["error"] == "RuntimeError: CUDA out of memory"
    assert failed["finished_at"] is not None
    assert not jobs.result_path(spool, job["id"]).exists()


def test_media_deleted_while_queued_fails_the_job(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, False)
    (media_root / "interview.mp4").unlink()

    make_worker(spool).run_once()

    failed = jobs.load_job(spool, job["id"])
    assert failed["status"] == "failed"
    assert failed["error"].startswith("FileNotFoundError:")


def test_media_escaping_the_root_fails_the_job(spool, media_root):
    job = jobs.create_job(spool, "../outside.mp4", None, False)
    (media_root.parent / "outside.mp4").write_bytes(b"x")

    make_worker(spool).run_once()

    assert jobs.load_job(spool, job["id"])["status"] == "failed"


def test_delete_requested_during_a_run_removes_the_job_after_it_finishes(
    spool, media_root
):
    job = jobs.create_job(spool, "interview.mp4", None, False)

    def transcribe(media, language, diarize, progress):
        jobs.update_job(spool, job["id"], delete_requested=True)
        return {"segments": []}

    make_worker(spool, transcribe).run_once()

    assert not (spool / job["id"]).exists()


def test_delete_requested_removes_a_failed_job_too(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, False)

    def transcribe(media, language, diarize, progress):
        jobs.update_job(spool, job["id"], delete_requested=True)
        raise RuntimeError("boom")

    make_worker(spool, transcribe).run_once()

    assert not (spool / job["id"]).exists()


def test_run_once_takes_the_oldest_job(spool, media_root):
    first = jobs.create_job(spool, "interview.mp4", None, False)
    second = jobs.create_job(spool, "interview.mp4", None, False)
    jobs.update_job(spool, first["id"], created_at="2026-07-08T14:00:00+00:00")
    jobs.update_job(spool, second["id"], created_at="2026-07-08T15:00:00+00:00")

    make_worker(spool).run_once()

    assert jobs.load_job(spool, first["id"])["status"] == "succeeded"
    assert jobs.load_job(spool, second["id"])["status"] == "queued"


def test_the_thread_drains_the_queue_and_stops(spool, media_root):
    job = jobs.create_job(spool, "interview.mp4", None, False)
    worker = Worker(spool, fake_transcribe, idle_sleep=0.01)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if jobs.load_job(spool, job["id"])["status"] == "succeeded":
                break
            time.sleep(0.01)
    finally:
        worker.stop()

    assert jobs.load_job(spool, job["id"])["status"] == "succeeded"
    assert not worker.thread.is_alive()


def test_startup_recovers_interrupted_jobs_and_sweeps(spool, media_root, monkeypatch):
    interrupted = jobs.create_job(spool, "interview.mp4", None, False)
    jobs.update_job(spool, interrupted["id"], status="running")
    expired = jobs.create_job(spool, "interview.mp4", None, False)
    jobs.update_job(
        spool, expired["id"], status="failed", finished_at="2020-01-01T00:00:00+00:00"
    )

    make_worker(spool).startup()

    assert jobs.load_job(spool, interrupted["id"])["status"] == "queued"
    assert jobs.load_job(spool, expired["id"]) is None
