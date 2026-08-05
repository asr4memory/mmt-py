from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import config
import jobs
from worker import Worker

VERSION = (Path(__file__).parent / "VERSION").read_text().strip()

DESCRIPTION = """
Automatic speech recognition based on [whisperX](https://github.com/m-bain/whisperX).

The service is format-agnostic: it returns whisperX's aligned output as-is and
knows nothing about the mmt transcript format. Media is referenced by a path on
shared storage, relative to `MEDIA_ROOT`, so no media bytes are transferred over
HTTP.

Transcription takes minutes to hours and one job occupies the GPU fully, so the
service is asynchronous around a queue of jobs which are processed one at a
time, in the order in which they were submitted: submit a job, poll its status,
fetch its result.
"""

TAGS_METADATA = [
    {
        "name": "health",
        "description": "Liveness of the service, for container health checks "
        "and monitoring.",
    },
    {
        "name": "jobs",
        "description": "Submit transcription jobs, list them, poll a single "
        "job, fetch its result and delete it.",
    },
]

JobState = Literal["queued", "running", "succeeded", "failed"]

# The default and the largest number of jobs one call to `GET /jobs` returns.
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


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


app = FastAPI(
    title="MMT ASR",
    summary="Transcription of media files, queued and processed one at a time.",
    description=DESCRIPTION,
    version=VERSION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)


class HealthResponse(BaseModel):
    """Liveness of the service."""

    status: str = Field(description="Always `ok`.", examples=["ok"])
    version: str = Field(description="Version of the service.", examples=[VERSION])


@app.get(
    "/health",
    tags=["health"],
    summary="Check that the service is up",
    description="Returns as soon as the process serves requests. Neither the "
    "spool directory nor the transcription model is read here, so a successful "
    "response says nothing about the state of the queue or of the model.",
    response_description="The service is up.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION)


class JobRequest(BaseModel):
    """The media file to transcribe, and how to transcribe it."""

    path: str = Field(
        description="Path of the media file, relative to `MEDIA_ROOT`. Any "
        "format ffmpeg can read.",
        examples=["user_files/abc/interview.mp4"],
    )
    language: str | None = Field(
        default=None,
        description="ISO 639-1 code of the spoken language. Omitted or `null` "
        "leaves the language to whisper's auto-detection.",
        examples=["de"],
    )
    diarize: bool = Field(
        default=False,
        description="Assign a speaker to every word. Requires `HF_TOKEN` to be "
        "configured, because the diarization models are gated.",
    )


class JobCreated(BaseModel):
    """The accepted job."""

    id: str = Field(description="Id of the job.", examples=["j_8f3ab2c1"])
    status: JobState = Field(description="Always `queued`.", examples=["queued"])


class JobStatus(BaseModel):
    """The state of one job."""

    id: str = Field(description="Id of the job.", examples=["j_8f3ab2c1"])
    status: JobState = Field(description="State of the job.", examples=["running"])
    progress: float = Field(
        description="Fraction of the work that is done, between 0 and 1. It is "
        "0 while the job is queued, increases monotonically while it runs, and "
        "is 1 once it has succeeded.",
        examples=[0.65],
    )
    created_at: str = Field(
        description="When the job was submitted, ISO 8601 in UTC.",
        examples=["2026-07-08T14:02:11+00:00"],
    )
    started_at: str | None = Field(
        description="When the worker picked the job up, `null` until then.",
        examples=["2026-07-08T14:05:03+00:00"],
    )
    finished_at: str | None = Field(
        description="When the job succeeded or failed, `null` until then.",
        examples=[None],
    )
    language: str | None = Field(
        description="The language given at submission, `null` if it was left "
        "to auto-detection. The detected language is part of the result, not "
        "of this response.",
        examples=["de"],
    )
    error: str | None = Field(
        description="Why the job failed, `null` in every other state. The key "
        "is always present, so that callers parse one response shape.",
        examples=[None],
    )


class JobSummary(JobStatus):
    """The state of one job, together with what it was submitted with."""

    path: str = Field(
        description="Path of the media file, relative to `MEDIA_ROOT`.",
        examples=["user_files/abc/interview.mp4"],
    )
    diarize: bool = Field(description="Whether speakers are assigned to words.")


class JobList(BaseModel):
    """One page of jobs, and how many jobs the filters matched in total."""

    total: int = Field(
        description="Number of jobs matching the filters, which is larger than "
        "the number of returned jobs when `limit` or `offset` cut the list.",
        examples=[3],
    )
    jobs: list[JobSummary] = Field(
        description="The matching jobs, oldest first, after `offset` and "
        "`limit` have been applied."
    )


def _load(job_id: str) -> dict:
    job = jobs.load_job(config.spool_dir(), job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job


def _as_utc(value: datetime) -> datetime:
    """Read a timestamp given without an offset as UTC, like the stored ones."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@app.post("/jobs", status_code=202, tags=["jobs"], summary="Submit a job")
def create_job(request: JobRequest) -> JobCreated:
    if config.resolve_media(request.path) is None:
        raise HTTPException(status_code=400, detail="media file not found")
    job = jobs.create_job(
        config.spool_dir(), request.path, request.language, request.diarize
    )
    return JobCreated(id=job["id"], status=job["status"])


@app.get(
    "/jobs",
    tags=["jobs"],
    summary="List jobs",
    description="Every job the service currently holds, oldest first by "
    "submission time, which is the order in which the worker runs them. Jobs "
    "are removed `RETENTION_DAYS` days after they finished, so this is not a "
    "complete history of everything ever submitted.\n\n"
    "The filters are combined with a logical and. A job matches `status` if "
    "its state is one of the given states, and the two timestamps are "
    "inclusive bounds on `created_at`.",
    response_description="The matching jobs and their total number.",
)
def get_jobs(
    status: Annotated[
        list[JobState] | None,
        Query(
            description="Keep only jobs in one of these states. Repeat the "
            "parameter for more than one state. Omitted means every state."
        ),
    ] = None,
    path: Annotated[
        str | None,
        Query(
            description="Keep only jobs submitted with exactly this media "
            "path, relative to `MEDIA_ROOT`.",
            examples=["user_files/abc/interview.mp4"],
        ),
    ] = None,
    created_after: Annotated[
        datetime | None,
        Query(
            description="Keep only jobs submitted at or after this time, ISO "
            "8601. A time without an offset is read as UTC.",
            examples=["2026-07-08T14:02:11+00:00"],
        ),
    ] = None,
    created_before: Annotated[
        datetime | None,
        Query(
            description="Keep only jobs submitted at or before this time, ISO "
            "8601. A time without an offset is read as UTC.",
            examples=["2026-07-08T18:00:00+00:00"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Largest number of jobs to return."),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        int, Query(ge=0, description="Number of matching jobs to skip.")
    ] = 0,
) -> JobList:
    found = jobs.list_jobs(config.spool_dir())
    if status is not None:
        found = [job for job in found if job["status"] in status]
    if path is not None:
        found = [job for job in found if job["path"] == path]
    if created_after is not None:
        after = _as_utc(created_after)
        found = [
            job for job in found if datetime.fromisoformat(job["created_at"]) >= after
        ]
    if created_before is not None:
        before = _as_utc(created_before)
        found = [
            job for job in found if datetime.fromisoformat(job["created_at"]) <= before
        ]
    found.sort(key=lambda job: (job["created_at"], job["id"]))
    page = found[offset : offset + limit]
    return JobList(
        total=len(found),
        jobs=[
            JobSummary(**{field: job[field] for field in JobSummary.model_fields})
            for job in page
        ],
    )


@app.get(
    "/jobs/{job_id}",
    tags=["jobs"],
    summary="Poll one job",
    responses={404: {"description": "Unknown job id."}},
)
def get_job(job_id: str) -> JobStatus:
    job = _load(job_id)
    return JobStatus(**{field: job[field] for field in JobStatus.model_fields})


@app.get(
    "/jobs/{job_id}/result",
    tags=["jobs"],
    summary="Fetch the transcript of a succeeded job",
    description="whisperX's aligned output, extended by the detected "
    "`language` and otherwise unchanged.",
    responses={
        404: {"description": "Unknown job id."},
        409: {"description": "The job has not succeeded, so it has no result."},
    },
)
def get_result(job_id: str) -> FileResponse:
    job = _load(job_id)
    if job["status"] != "succeeded":
        raise HTTPException(status_code=409, detail=f"job is {job['status']}")
    return FileResponse(jobs.result_path(config.spool_dir(), job_id))


@app.delete(
    "/jobs/{job_id}",
    status_code=204,
    tags=["jobs"],
    summary="Delete a job",
    description="Cancels a queued job and removes a finished job with its "
    "result. A running job is marked instead and removed once it finishes, "
    "because running jobs are not cancelled.",
    responses={404: {"description": "Unknown job id."}},
)
def delete_job(job_id: str) -> Response:
    spool = config.spool_dir()
    job = _load(job_id)
    if job["status"] == "running":
        # The worker removes the directory once the job finishes.
        jobs.update_job(spool, job_id, delete_requested=True)
    else:
        jobs.delete_job(spool, job_id)
    return Response(status_code=204)
