"""The job store: a spool directory with one subdirectory per job.

`job.json` is the single source of truth for a job; queue order is derived
by scanning, never stored. Writes are atomic (temp file + `os.replace`),
so a crash mid-write can never leave a half-written job file behind.
"""

import json
import os
import re
import secrets
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

JOB_FILE = "job.json"
RESULT_FILE = "result.json"

TERMINAL_STATUSES = ("succeeded", "failed")

# The smallest progress change that is worth a write.
PROGRESS_STEP = 0.01

_JOB_ID = re.compile(r"^j_[0-9a-f]{8}$")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def job_dir(spool: Path, job_id: str) -> Path | None:
    """The job's directory, or None if `job_id` is not a valid id."""
    if not _JOB_ID.match(job_id):
        return None
    return spool / job_id


def result_path(spool: Path, job_id: str) -> Path:
    return spool / job_id / RESULT_FILE


def _write_job(spool: Path, job: dict) -> dict:
    directory = spool / job["id"]
    temp = directory / f".{JOB_FILE}.{secrets.token_hex(4)}"
    temp.write_text(json.dumps(job, indent=2))
    os.replace(temp, directory / JOB_FILE)
    return job


def create_job(spool: Path, path: str, language: str | None, diarize: bool) -> dict:
    spool.mkdir(parents=True, exist_ok=True)
    while True:
        job_id = "j_" + secrets.token_hex(4)
        try:
            (spool / job_id).mkdir()
        except FileExistsError:
            continue
        break
    return _write_job(
        spool,
        {
            "id": job_id,
            "status": "queued",
            "path": path,
            "language": language,
            "diarize": diarize,
            "progress": 0.0,
            "error": None,
            "delete_requested": False,
            "created_at": now(),
            "started_at": None,
            "finished_at": None,
        },
    )


def load_job(spool: Path, job_id: str) -> dict | None:
    directory = job_dir(spool, job_id)
    if directory is None:
        return None
    try:
        return json.loads((directory / JOB_FILE).read_text())
    except FileNotFoundError:
        return None


def update_job(spool: Path, job_id: str, **fields) -> dict:
    """Merge `fields` into the job and rewrite `job.json` atomically."""
    job = load_job(spool, job_id)
    if job is None:
        raise KeyError(job_id)
    return _write_job(spool, job | fields)


def set_progress(spool: Path, job_id: str, progress: float) -> None:
    """Persist progress, clamped monotonic and throttled to `PROGRESS_STEP`."""
    job = load_job(spool, job_id)
    if job is None:
        return
    progress = min(1.0, max(0.0, progress))
    if progress < job["progress"] + PROGRESS_STEP:
        return
    update_job(spool, job_id, progress=progress)


def list_jobs(spool: Path) -> list[dict]:
    if not spool.is_dir():
        return []
    jobs = (load_job(spool, directory.name) for directory in spool.iterdir())
    return [job for job in jobs if job is not None]


def next_queued(spool: Path) -> dict | None:
    """The oldest queued job, by (`created_at`, `id`)."""
    queued = [job for job in list_jobs(spool) if job["status"] == "queued"]
    if not queued:
        return None
    return min(queued, key=lambda job: (job["created_at"], job["id"]))


def recover_interrupted(spool: Path) -> None:
    """Reset jobs left `running` by a crash back to `queued`."""
    for job in list_jobs(spool):
        if job["status"] == "running":
            update_job(spool, job["id"], status="queued")


def sweep_expired(spool: Path, retention_days: int) -> None:
    """Remove finished jobs whose `finished_at` is past retention."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    for job in list_jobs(spool):
        if job["status"] not in TERMINAL_STATUSES or not job["finished_at"]:
            continue
        if datetime.fromisoformat(job["finished_at"]) < cutoff:
            delete_job(spool, job["id"])


def delete_job(spool: Path, job_id: str) -> None:
    directory = job_dir(spool, job_id)
    if directory is not None:
        shutil.rmtree(directory, ignore_errors=True)
