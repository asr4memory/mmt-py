import json
from datetime import UTC, datetime, timedelta

import pytest

import jobs


@pytest.fixture
def spool(tmp_path):
    return tmp_path / "spool"


def read_job_file(spool, job_id):
    return json.loads((spool / job_id / "job.json").read_text())


def test_create_job_writes_the_full_field_set(spool):
    job = jobs.create_job(spool, "user_files/abc/interview.mp4", "de", False)

    assert job["id"].startswith("j_")
    assert len(job["id"]) == len("j_8f3ab2c1")
    assert job == {
        "id": job["id"],
        "status": "queued",
        "path": "user_files/abc/interview.mp4",
        "language": "de",
        "diarize": False,
        "progress": 0.0,
        "error": None,
        "delete_requested": False,
        "created_at": job["created_at"],
        "started_at": None,
        "finished_at": None,
    }
    assert read_job_file(spool, job["id"]) == job


def test_create_job_timestamps_in_utc_seconds(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)

    created_at = datetime.fromisoformat(job["created_at"])
    assert created_at.tzinfo == UTC
    assert created_at.microsecond == 0


def test_create_job_ids_are_unique(spool):
    ids = {jobs.create_job(spool, "a.mp4", None, False)["id"] for _ in range(20)}

    assert len(ids) == 20


def test_load_job_returns_none_for_unknown_id(spool):
    spool.mkdir()

    assert jobs.load_job(spool, "j_deadbeef") is None


def test_load_job_returns_none_for_a_traversing_id(spool):
    jobs.create_job(spool, "a.mp4", None, False)

    assert jobs.load_job(spool, "../spool") is None


def test_update_job_persists_a_status_transition(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)

    updated = jobs.update_job(spool, job["id"], status="running", started_at="now")

    assert updated["status"] == "running"
    assert updated["started_at"] == "now"
    assert updated["path"] == "a.mp4"
    assert read_job_file(spool, job["id"]) == updated


def test_update_job_writes_atomically_and_leaves_no_temp_files(spool, monkeypatch):
    job = jobs.create_job(spool, "a.mp4", None, False)
    replaced = []
    real_replace = jobs.os.replace

    def spy(src, dst):
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(jobs.os, "replace", spy)
    jobs.update_job(spool, job["id"], status="running")

    src, dst = replaced[-1]
    assert dst.endswith("/job.json")
    assert src != dst
    assert sorted(p.name for p in (spool / job["id"]).iterdir()) == ["job.json"]


def test_update_job_on_unknown_id_raises(spool):
    spool.mkdir()

    with pytest.raises(KeyError):
        jobs.update_job(spool, "j_deadbeef", status="running")


def test_next_queued_takes_the_oldest_job(spool):
    old = jobs.create_job(spool, "old.mp4", None, False)
    new = jobs.create_job(spool, "new.mp4", None, False)
    jobs.update_job(spool, old["id"], created_at="2026-07-08T14:00:00+00:00")
    jobs.update_job(spool, new["id"], created_at="2026-07-08T14:00:01+00:00")

    assert jobs.next_queued(spool)["id"] == old["id"]


def test_next_queued_breaks_ties_by_id(spool):
    first = jobs.create_job(spool, "a.mp4", None, False)
    second = jobs.create_job(spool, "b.mp4", None, False)
    for job in (first, second):
        jobs.update_job(spool, job["id"], created_at="2026-07-08T14:00:00+00:00")

    expected = min(first["id"], second["id"])
    assert jobs.next_queued(spool)["id"] == expected


def test_next_queued_ignores_jobs_that_are_not_queued(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)
    jobs.update_job(spool, job["id"], status="running")

    assert jobs.next_queued(spool) is None


def test_next_queued_on_an_empty_spool(spool):
    assert jobs.next_queued(spool) is None


def test_recover_interrupted_resets_running_jobs_and_nothing_else(spool):
    running = jobs.create_job(spool, "a.mp4", None, False)
    jobs.update_job(
        spool,
        running["id"],
        status="running",
        started_at="2026-07-08T14:00:00+00:00",
        progress=0.4,
    )
    queued = jobs.create_job(spool, "b.mp4", None, False)
    succeeded = jobs.create_job(spool, "c.mp4", None, False)
    jobs.update_job(spool, succeeded["id"], status="succeeded", progress=1.0)

    jobs.recover_interrupted(spool)

    recovered = jobs.load_job(spool, running["id"])
    assert recovered["status"] == "queued"
    assert recovered["started_at"] == "2026-07-08T14:00:00+00:00"
    assert recovered["progress"] == 0.4
    assert jobs.load_job(spool, queued["id"])["status"] == "queued"
    assert jobs.load_job(spool, succeeded["id"])["status"] == "succeeded"


def _finished(spool, path, status, days_ago):
    job = jobs.create_job(spool, path, None, False)
    finished_at = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(
        timespec="seconds"
    )
    return jobs.update_job(spool, job["id"], status=status, finished_at=finished_at)


def test_sweep_expired_removes_finished_jobs_past_retention(spool):
    old_success = _finished(spool, "a.mp4", "succeeded", days_ago=8)
    old_failure = _finished(spool, "b.mp4", "failed", days_ago=8)
    fresh = _finished(spool, "c.mp4", "succeeded", days_ago=1)
    queued = jobs.create_job(spool, "d.mp4", None, False)

    jobs.sweep_expired(spool, retention_days=7)

    assert not (spool / old_success["id"]).exists()
    assert not (spool / old_failure["id"]).exists()
    assert jobs.load_job(spool, fresh["id"]) is not None
    assert jobs.load_job(spool, queued["id"]) is not None


def test_sweep_expired_keeps_a_long_running_job(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)
    long_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat(timespec="seconds")
    jobs.update_job(spool, job["id"], status="running", started_at=long_ago)

    jobs.sweep_expired(spool, retention_days=7)

    assert jobs.load_job(spool, job["id"]) is not None


def test_delete_job_removes_the_spool_directory(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)

    jobs.delete_job(spool, job["id"])

    assert not (spool / job["id"]).exists()


def test_set_progress_persists_a_change_of_at_least_one_percent(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)

    jobs.set_progress(spool, job["id"], 0.01)

    assert read_job_file(spool, job["id"])["progress"] == pytest.approx(0.01)


def test_set_progress_throttles_smaller_changes(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)
    jobs.set_progress(spool, job["id"], 0.5)

    jobs.set_progress(spool, job["id"], 0.505)

    assert read_job_file(spool, job["id"])["progress"] == pytest.approx(0.5)


def test_set_progress_never_moves_backwards(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)
    jobs.set_progress(spool, job["id"], 0.7)

    jobs.set_progress(spool, job["id"], 0.1)

    assert read_job_file(spool, job["id"])["progress"] == pytest.approx(0.7)


def test_set_progress_clamps_to_the_unit_interval(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)

    jobs.set_progress(spool, job["id"], 1.5)

    assert read_job_file(spool, job["id"])["progress"] == pytest.approx(1.0)


def test_set_progress_on_a_deleted_job_is_a_no_op(spool):
    job = jobs.create_job(spool, "a.mp4", None, False)
    jobs.delete_job(spool, job["id"])

    jobs.set_progress(spool, job["id"], 0.5)

    assert jobs.load_job(spool, job["id"]) is None
