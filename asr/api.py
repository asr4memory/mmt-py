from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

import config
import jobs
from worker import Worker

VERSION = (Path(__file__).parent / "VERSION").read_text().strip()

DESCRIPTION = """
Automatic speech recognition based on
[whisperX](https://github.com/m-bain/whisperX).

The service is format-agnostic: it knows nothing about the mmt transcript
format and returns whisperX's aligned output as-is.

* Media is referenced by a path on shared storage, relative to `MEDIA_ROOT`.
  No media bytes are sent to or from this service.
* Transcription takes minutes to hours and the model runs one job at a time,
  so the API is asynchronous around a job queue: submit a job with
  `POST /jobs`, poll it with `GET /jobs/{job_id}`, fetch the transcription
  with `GET /jobs/{job_id}/result`.
* Jobs survive a restart of the service. A job that was `running` when the
  process stopped is reset to `queued` and runs again from the beginning.
* Finished jobs are removed after `RETENTION_DAYS` days. An id that is no
  longer known answers `404`, which the caller treats as "gone, resubmit".
"""

CREATE_JOB_DESCRIPTION = """
Puts a job into the queue. The response is returned before any transcription
work runs; the job starts once the worker is free.

`path` is relative to `MEDIA_ROOT` and must resolve to an existing file
underneath it. A path that points outside `MEDIA_ROOT`, for example through
`..`, is rejected with `400`, as is a path that does not exist.

`language` is passed to whisperX as the spoken language of the recording.
When it is `null`, whisperX detects the language itself. The detected
language is part of the result, not of the job status.

Diarization (`diarize: true`) attaches a speaker to every word. It uses the
gated pyannote models and therefore needs `HF_TOKEN` to be set on the service;
without it the job fails before any transcription work runs.
"""

JOB_STATUS_DESCRIPTION = """
Reports the state of one job. This is the endpoint to poll while a job runs.

`status` is one of:

| Status | Meaning |
| --- | --- |
| `queued` | The job waits for the worker. |
| `running` | The worker transcribes the media file. |
| `succeeded` | The result can be fetched from `/jobs/{job_id}/result`. |
| `failed` | The job will not produce a result; `error` says why. |

`progress` only grows, and it is written in steps of about one percent rather
than continuously. It covers transcription, alignment and, when requested,
diarization, so it does not advance at a constant rate.
"""

RESULT_DESCRIPTION = """
Returns whisperX's aligned output for a succeeded job, unchanged except for
two added fields: `language`, the language the transcription was made in, and
`model`, the whisper model it ran with.

The result is available only while the job is `succeeded`. A job that is
`queued`, `running` or `failed` answers `409`, and an id that is unknown, or
whose job was deleted or swept, answers `404`.
"""

DELETE_DESCRIPTION = """
Removes a job and its result. A `queued` job is cancelled and never runs. A
`running` job is marked for removal and is removed by the worker once the
current job finishes; the transcription itself is not interrupted. A finished
job is removed immediately.

Deleting is not required: finished jobs are swept after `RETENTION_DAYS`
days.
"""

EXAMPLE_REQUEST = {
    "path": "user_files/abc/interview.mp4",
    "language": "de",
    "diarize": False,
}

EXAMPLE_CREATED = {"id": "j_8f3ab2c1", "status": "queued"}

EXAMPLE_STATUS = {
    "id": "j_8f3ab2c1",
    "status": "running",
    "progress": 0.65,
    "created_at": "2026-07-08T14:02:11+00:00",
    "started_at": "2026-07-08T14:05:03+00:00",
    "finished_at": None,
    "language": "de",
    "error": None,
}

EXAMPLE_RESULT = {
    "segments": [
        {
            "start": 0.31,
            "end": 3.12,
            "text": " Angela Merkel besuchte Berlin.",
            "words": [
                {"word": "Angela", "start": 0.31, "end": 0.78, "score": 0.91},
                {"word": "Merkel", "start": 0.82, "end": 1.36, "score": 0.94},
            ],
        }
    ],
    "word_segments": [
        {"word": "Angela", "start": 0.31, "end": 0.78, "score": 0.91},
        {"word": "Merkel", "start": 0.82, "end": 1.36, "score": 0.94},
    ],
    "language": "de",
    "model": "large-v3",
}


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
    title="ASR Service",
    summary="Speech recognition over media files on shared storage.",
    description=DESCRIPTION,
    lifespan=lifespan,
    version=VERSION,
)


class HealthResponse(BaseModel):
    """Liveness of the service."""

    status: str = Field(description="Always `ok`.", examples=["ok"])
    version: str = Field(description="Version of the service.", examples=[VERSION])


@app.get(
    "/health",
    summary="Check that the service is up",
    description="Returns as soon as the process serves requests. It says "
    "nothing about the worker, the spool or the model cache, so a successful "
    "response does not mean that a job can run. This is the endpoint the "
    "container health check calls.",
    response_description="The service is up.",
)
def health() -> HealthResponse:
    """Report that the process serves requests. Says nothing about the worker."""
    return HealthResponse(status="ok", version=VERSION)


class JobRequest(BaseModel):
    """The media file to transcribe."""

    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_REQUEST]})

    path: str = Field(
        description="Path of the media file, relative to `MEDIA_ROOT`. It "
        "must resolve to an existing file underneath `MEDIA_ROOT`.",
        examples=["user_files/abc/interview.mp4"],
    )
    language: str | None = Field(
        default=None,
        description="Language of the recording as an ISO 639-1 code. `null` "
        "lets whisperX detect the language itself.",
        examples=["de"],
    )
    diarize: bool = Field(
        default=False,
        description="Attach a speaker to every word. Requires `HF_TOKEN` on "
        "the service; without it the job fails before any transcription work "
        "runs.",
        examples=[False],
    )


class JobCreated(BaseModel):
    """The id under which the new job is queued."""

    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CREATED]})

    id: str = Field(
        description="Id of the job, used in every other job endpoint.",
        examples=["j_8f3ab2c1"],
    )
    status: str = Field(
        description="Status of the new job, always `queued`.", examples=["queued"]
    )


class JobStatus(BaseModel):
    """State of one job."""

    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_STATUS]})

    id: str = Field(description="Id of the job.", examples=["j_8f3ab2c1"])
    status: str = Field(
        description="One of `queued`, `running`, `succeeded`, `failed`.",
        examples=["running"],
    )
    progress: float = Field(
        description="Fraction of the work that is done, from 0 to 1. It only "
        "grows and is written in steps of about one percent.",
        examples=[0.65],
    )
    created_at: str = Field(
        description="ISO 8601 time at which the job was submitted.",
        examples=["2026-07-08T14:02:11+00:00"],
    )
    started_at: str | None = Field(
        description="ISO 8601 time at which the worker picked the job up, "
        "`null` while it is queued.",
        examples=["2026-07-08T14:05:03+00:00"],
    )
    finished_at: str | None = Field(
        description="ISO 8601 time at which the job succeeded or failed, "
        "`null` before that.",
        examples=[None],
    )
    language: str | None = Field(
        description="The language requested when the job was submitted, "
        "`null` when none was requested. The language whisperX detected is "
        "part of the result, not of this response.",
        examples=["de"],
    )
    error: str | None = Field(
        description="Why the job failed, `null` for every other status.",
        examples=[None],
    )


def _load(job_id: str) -> dict:
    job = jobs.load_job(config.spool_dir(), job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job


@app.post(
    "/jobs",
    status_code=202,
    summary="Submit a media file for transcription",
    description=CREATE_JOB_DESCRIPTION,
    response_description="The job is queued.",
    responses={
        400: {
            "description": "`path` does not exist under `MEDIA_ROOT` or points "
            "outside it."
        },
        422: {"description": "`path` is missing or a field has the wrong type."},
    },
)
def create_job(request: JobRequest) -> JobCreated:
    if config.resolve_media(request.path) is None:
        raise HTTPException(status_code=400, detail="media file not found")
    job = jobs.create_job(
        config.spool_dir(), request.path, request.language, request.diarize
    )
    return JobCreated(id=job["id"], status=job["status"])


@app.get(
    "/jobs/{job_id}",
    summary="Read the status of a job",
    description=JOB_STATUS_DESCRIPTION,
    response_description="The current state of the job.",
    responses={404: {"description": "No job with this id."}},
)
def get_job(job_id: str) -> JobStatus:
    job = _load(job_id)
    return JobStatus(**{field: job[field] for field in JobStatus.model_fields})


@app.get(
    "/jobs/{job_id}/result",
    summary="Fetch the transcription of a succeeded job",
    description=RESULT_DESCRIPTION,
    response_class=FileResponse,
    response_description="whisperX's aligned output, plus the `language` the "
    "transcription was made in and the `model` it ran with.",
    responses={
        200: {"content": {"application/json": {"example": EXAMPLE_RESULT}}},
        404: {"description": "No job with this id."},
        409: {"description": "The job is not `succeeded`, so it has no result."},
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
    summary="Cancel or remove a job",
    description=DELETE_DESCRIPTION,
    response_description="The job is removed, or marked for removal while it "
    "still runs.",
    responses={404: {"description": "No job with this id."}},
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
