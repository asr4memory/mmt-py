import json

import pytest
from fastapi.testclient import TestClient

import api
import jobs


@pytest.fixture
def spool(tmp_path):
    return tmp_path / "spool"


@pytest.fixture
def media_root(tmp_path):
    root = tmp_path / "media"
    (root / "user_files").mkdir(parents=True)
    (root / "user_files" / "interview.mp4").write_bytes(b"fake media")
    (tmp_path / "outside.mp4").write_bytes(b"secret")
    return root


@pytest.fixture
def client(monkeypatch, spool, media_root):
    """A client whose worker never runs: the tests drive job state directly."""
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("SPOOL_DIR", str(spool))
    monkeypatch.setattr(api, "start_worker", lambda spool: None)
    with TestClient(api.app) as client:
        yield client


def submit(client, path="user_files/interview.mp4", **body):
    return client.post("/jobs", json={"path": path, **body})


def test_post_jobs_creates_a_queued_job(client, spool):
    response = submit(client, language="de")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    job = jobs.load_job(spool, body["id"])
    assert job["path"] == "user_files/interview.mp4"
    assert job["language"] == "de"
    assert job["diarize"] is False


def test_post_jobs_defaults_language_and_diarize(client, spool):
    job = jobs.load_job(spool, submit(client).json()["id"])

    assert job["language"] is None
    assert job["diarize"] is False


def test_post_jobs_accepts_diarize(client, spool):
    job = jobs.load_job(spool, submit(client, diarize=True).json()["id"])

    assert job["diarize"] is True


def test_post_jobs_rejects_a_path_missing_on_disk(client, spool):
    response = submit(client, path="user_files/nope.mp4")

    assert response.status_code == 400
    assert jobs.list_jobs(spool) == []


def test_post_jobs_rejects_a_path_escaping_the_media_root(client):
    assert submit(client, path="../outside.mp4").status_code == 400
    assert submit(client, path="user_files/../../outside.mp4").status_code == 400


def test_post_jobs_rejects_an_absolute_path(client, media_root):
    outside = media_root.parent / "outside.mp4"

    assert submit(client, path=str(outside)).status_code == 400


def test_post_jobs_rejects_a_directory(client):
    assert submit(client, path="user_files").status_code == 400


def test_post_jobs_rejects_a_malformed_body(client):
    assert client.post("/jobs", json={"language": "de"}).status_code == 422
    assert submit(client, diarize="maybe").status_code == 422


def test_get_job_returns_the_status_object(client, spool):
    job_id = submit(client, language="de").json()["id"]
    jobs.update_job(
        spool,
        job_id,
        status="running",
        progress=0.65,
        started_at="2026-07-08T14:05:03+00:00",
    )

    body = client.get(f"/jobs/{job_id}").json()

    assert body == {
        "id": job_id,
        "status": "running",
        "progress": 0.65,
        "created_at": jobs.load_job(spool, job_id)["created_at"],
        "started_at": "2026-07-08T14:05:03+00:00",
        "finished_at": None,
        "language": "de",
        "error": None,
    }


def test_get_job_reports_the_error_of_a_failed_job(client, spool):
    job_id = submit(client).json()["id"]
    jobs.update_job(spool, job_id, status="failed", error="RuntimeError: boom")

    assert client.get(f"/jobs/{job_id}").json()["error"] == "RuntimeError: boom"


def test_get_job_unknown_id(client):
    assert client.get("/jobs/j_deadbeef").status_code == 404


def test_get_result_returns_the_whisperx_output_as_is(client, spool):
    job_id = submit(client).json()["id"]
    result = {"language": "de", "segments": [{"start": 0.02, "text": "Guten Tag"}]}
    jobs.result_path(spool, job_id).write_text(json.dumps(result))
    jobs.update_job(spool, job_id, status="succeeded", progress=1.0)

    response = client.get(f"/jobs/{job_id}/result")

    assert response.status_code == 200
    assert response.json() == result


def test_get_result_unknown_id(client):
    assert client.get("/jobs/j_deadbeef/result").status_code == 404


@pytest.mark.parametrize("status", ["queued", "running", "failed"])
def test_get_result_before_success_is_a_conflict(client, spool, status):
    job_id = submit(client).json()["id"]
    jobs.update_job(spool, job_id, status=status)

    assert client.get(f"/jobs/{job_id}/result").status_code == 409


def test_delete_removes_a_queued_job(client, spool):
    job_id = submit(client).json()["id"]

    assert client.delete(f"/jobs/{job_id}").status_code == 204
    assert jobs.load_job(spool, job_id) is None


def test_delete_removes_a_finished_job_and_its_artifacts(client, spool):
    job_id = submit(client).json()["id"]
    jobs.result_path(spool, job_id).write_text("{}")
    jobs.update_job(spool, job_id, status="succeeded")

    assert client.delete(f"/jobs/{job_id}").status_code == 204
    assert not (spool / job_id).exists()


def test_delete_only_marks_a_running_job(client, spool):
    job_id = submit(client).json()["id"]
    jobs.update_job(spool, job_id, status="running")

    assert client.delete(f"/jobs/{job_id}").status_code == 204
    job = jobs.load_job(spool, job_id)
    assert job["status"] == "running"
    assert job["delete_requested"] is True


def test_delete_unknown_id(client):
    assert client.delete("/jobs/j_deadbeef").status_code == 404
