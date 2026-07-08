from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
import jobs
from worker import Worker


def start_worker(spool: Path) -> Worker:
    """Start the transcription worker. Imported lazily: whisperx is heavy."""
    from transcriber import transcribe

    worker = Worker(spool, transcribe)
    worker.start()
    return worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = start_worker(config.spool_dir())
    yield
    if worker is not None:
        worker.stop()


app = FastAPI(title="MMT ASR", lifespan=lifespan)


class JobRequest(BaseModel):
    path: str
    language: str | None = None
    diarize: bool = False


class JobCreated(BaseModel):
    id: str
    status: str


class JobStatus(BaseModel):
    id: str
    status: str
    progress: float
    created_at: str
    started_at: str | None
    finished_at: str | None
    language: str | None
    error: str | None


def _load(job_id: str) -> dict:
    job = jobs.load_job(config.spool_dir(), job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job


@app.post("/jobs", status_code=202)
def create_job(request: JobRequest) -> JobCreated:
    if config.resolve_media(request.path) is None:
        raise HTTPException(status_code=400, detail="media file not found")
    job = jobs.create_job(
        config.spool_dir(), request.path, request.language, request.diarize
    )
    return JobCreated(id=job["id"], status=job["status"])


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> JobStatus:
    job = _load(job_id)
    return JobStatus(**{field: job[field] for field in JobStatus.model_fields})


@app.get("/jobs/{job_id}/result")
def get_result(job_id: str) -> FileResponse:
    job = _load(job_id)
    if job["status"] != "succeeded":
        raise HTTPException(status_code=409, detail=f"job is {job['status']}")
    return FileResponse(jobs.result_path(config.spool_dir(), job_id))


@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> Response:
    spool = config.spool_dir()
    job = _load(job_id)
    if job["status"] == "running":
        # The worker removes the directory once the job finishes.
        jobs.update_job(spool, job_id, delete_requested=True)
    else:
        jobs.delete_job(spool, job_id)
    return Response(status_code=204)
