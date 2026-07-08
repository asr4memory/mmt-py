"""The worker thread: one job at a time, oldest queued first.

Concurrency is 1 by design — whisperx saturates the GPU, so queueing *is*
the feature. `transcribe` is injected, which keeps whisperx out of the
tests.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import config
import jobs

if TYPE_CHECKING:  # transcriber imports whisperx; the worker only needs the type
    from transcriber import Transcribe

logger = logging.getLogger(__name__)

IDLE_SLEEP = 1.0


class Worker:
    def __init__(
        self,
        spool: Path,
        transcribe: Transcribe,
        idle_sleep: float = IDLE_SLEEP,
    ):
        self.spool = spool
        self.transcribe = transcribe
        self.idle_sleep = idle_sleep
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run_forever, daemon=True)

    def start(self) -> None:
        self.startup()
        self.thread.start()

    def stop(self) -> None:
        self.stopped.set()
        if self.thread.is_alive():
            self.thread.join(timeout=5)

    def startup(self) -> None:
        """Recover jobs interrupted by a crash, then drop expired ones."""
        self.spool.mkdir(parents=True, exist_ok=True)
        jobs.recover_interrupted(self.spool)
        jobs.sweep_expired(self.spool, config.retention_days())

    def run_forever(self) -> None:
        while not self.stopped.is_set():
            try:
                if self.run_once():
                    continue
                jobs.sweep_expired(self.spool, config.retention_days())
            except Exception:
                logger.exception("worker loop failed")
            self.stopped.wait(self.idle_sleep)

    def run_once(self) -> bool:
        """Run the oldest queued job, if there is one."""
        job = jobs.next_queued(self.spool)
        if job is None:
            return False

        job_id = job["id"]
        jobs.update_job(self.spool, job_id, status="running", started_at=jobs.now())
        try:
            result = self._transcribe(job)
        except Exception as exc:
            logger.exception("job %s failed", job_id)
            self._finish(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        else:
            self._write_result(job_id, result)
            self._finish(job_id, status="succeeded", progress=1.0)
        return True

    def _transcribe(self, job: dict) -> dict:
        # The file may have been deleted while the job sat in the queue.
        media = config.resolve_media(job["path"])
        if media is None:
            raise FileNotFoundError(job["path"])
        job_id = job["id"]
        return self.transcribe(
            media,
            job["language"],
            job["diarize"],
            lambda value: jobs.set_progress(self.spool, job_id, value),
        )

    def _write_result(self, job_id: str, result: dict) -> None:
        path = jobs.result_path(self.spool, job_id)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(result))
        os.replace(temp, path)

    def _finish(self, job_id: str, **fields) -> None:
        job = jobs.update_job(self.spool, job_id, finished_at=jobs.now(), **fields)
        if job["delete_requested"]:
            jobs.delete_job(self.spool, job_id)
