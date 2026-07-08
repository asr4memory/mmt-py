"""Environment configuration, read on every call so tests can monkeypatch."""

import os
from pathlib import Path


def media_root() -> Path:
    """Mount point of the shared media storage (read-only)."""
    return Path(os.environ["MEDIA_ROOT"]).resolve()


def spool_dir() -> Path:
    return Path(os.environ.get("SPOOL_DIR", "./spool")).resolve()


def retention_days() -> int:
    return int(os.environ.get("RETENTION_DAYS", "7"))


def whisperx_model() -> str:
    return os.environ.get("WHISPERX_MODEL", "large-v3")


def whisperx_device() -> str:
    return os.environ.get("WHISPERX_DEVICE", "cuda")


def whisperx_compute_type() -> str:
    return os.environ.get("WHISPERX_COMPUTE_TYPE", "float16")


def whisperx_batch_size() -> int:
    return int(os.environ.get("WHISPERX_BATCH_SIZE", "16"))


def resolve_media(path: str) -> Path | None:
    """Resolve `path` under `MEDIA_ROOT`; None if it escapes or is missing."""
    root = media_root()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate
