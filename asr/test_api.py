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
    (root / "user_files" / "lecture.mp4").write_bytes(b"fake media")
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


def test_health_reports_ok_and_version(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": api.VERSION}


def test_health_does_not_need_the_spool_directory(client, spool):
    """The health check must stay cheap: it must not read or create the spool."""
    assert not spool.exists()

    assert client.get("/health").status_code == 200
    assert not spool.exists()


def test_openapi_separates_the_health_and_jobs_tags(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert paths["/health"]["get"]["tags"] == ["health"]
    assert [
        operation["tags"]
        for path, operations in paths.items()
        if path != "/health"
        for operation in operations.values()
    ] == [["jobs"]] * 5


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


def register(client, spool, path="user_files/interview.mp4", **fields):
    """Submit a job, then force fields such as `status` or `created_at` on it."""
    job_id = submit(client, path=path).json()["id"]
    if fields:
        jobs.update_job(spool, job_id, **fields)
    return job_id


def test_get_jobs_on_an_empty_spool(client):
    assert client.get("/jobs").json() == {"total": 0, "jobs": []}


def test_get_jobs_returns_every_job_oldest_first(client, spool):
    second = register(client, spool, created_at="2026-07-08T15:00:00+00:00")
    first = register(client, spool, created_at="2026-07-08T14:00:00+00:00")
    third = register(client, spool, created_at="2026-07-08T16:00:00+00:00")

    body = client.get("/jobs").json()

    assert [job["id"] for job in body["jobs"]] == [first, second, third]
    assert body["total"] == 3


def test_get_jobs_reports_the_full_job_summary(client, spool):
    job_id = submit(client, language="de", diarize=True).json()["id"]
    jobs.update_job(
        spool,
        job_id,
        status="running",
        progress=0.65,
        started_at="2026-07-08T14:05:03+00:00",
    )

    assert client.get("/jobs").json()["jobs"] == [
        {
            "id": job_id,
            "status": "running",
            "progress": 0.65,
            "created_at": jobs.load_job(spool, job_id)["created_at"],
            "started_at": "2026-07-08T14:05:03+00:00",
            "finished_at": None,
            "language": "de",
            "error": None,
            "path": "user_files/interview.mp4",
            "diarize": True,
        }
    ]


def test_get_jobs_filters_by_status(client, spool):
    running = register(client, spool, status="running")
    register(client, spool, status="succeeded")
    register(client, spool)

    body = client.get("/jobs?status=running").json()

    assert [job["id"] for job in body["jobs"]] == [running]
    assert body["total"] == 1


def test_get_jobs_accepts_several_statuses(client, spool):
    queued = register(client, spool, created_at="2026-07-08T14:00:00+00:00")
    failed = register(
        client, spool, status="failed", created_at="2026-07-08T15:00:00+00:00"
    )
    register(client, spool, status="succeeded")

    response = client.get("/jobs?status=queued&status=failed")

    assert [job["id"] for job in response.json()["jobs"]] == [queued, failed]


def test_get_jobs_rejects_an_unknown_status(client):
    assert client.get("/jobs?status=pending").status_code == 422


def test_get_jobs_filters_by_path(client, spool):
    interview = register(client, spool, path="user_files/interview.mp4")
    register(client, spool, path="user_files/lecture.mp4")

    body = client.get("/jobs?path=user_files/interview.mp4").json()

    assert [job["id"] for job in body["jobs"]] == [interview]


def test_get_jobs_filters_by_creation_time(client, spool):
    register(client, spool, created_at="2026-07-08T14:00:00+00:00")
    inside = register(client, spool, created_at="2026-07-08T15:00:00+00:00")
    register(client, spool, created_at="2026-07-08T16:00:00+00:00")

    body = client.get(
        "/jobs",
        params={
            "created_after": "2026-07-08T15:00:00+00:00",
            "created_before": "2026-07-08T15:00:00+00:00",
        },
    ).json()

    assert [job["id"] for job in body["jobs"]] == [inside]


def test_get_jobs_reads_a_timestamp_without_an_offset_as_utc(client, spool):
    job_id = register(client, spool, created_at="2026-07-08T15:00:00+00:00")

    body = client.get("/jobs?created_after=2026-07-08T14:59:59").json()

    assert [job["id"] for job in body["jobs"]] == [job_id]


def test_get_jobs_rejects_a_malformed_timestamp(client):
    assert client.get("/jobs?created_after=yesterday").status_code == 422


def test_get_jobs_returns_one_page_and_the_total(client, spool):
    ids = [
        register(client, spool, created_at=f"2026-07-08T1{hour}:00:00+00:00")
        for hour in range(4)
    ]

    body = client.get("/jobs?limit=2&offset=1").json()

    assert [job["id"] for job in body["jobs"]] == ids[1:3]
    assert body["total"] == 4


def test_get_jobs_counts_only_the_matching_jobs(client, spool):
    register(client, spool, status="succeeded")
    register(client, spool, status="succeeded")
    register(client, spool)

    assert client.get("/jobs?status=succeeded&limit=1").json()["total"] == 2


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=1001", "offset=-1", "limit=all"]
)
def test_get_jobs_rejects_an_invalid_page(client, query):
    assert client.get(f"/jobs?{query}").status_code == 422


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
