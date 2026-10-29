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


def models_file() -> Path:
    """The model registry; the image ships one, the operator mounts their own."""
    return Path(os.environ.get("MODELS_FILE", "/etc/mmt-asr/models.toml"))


def whisperx_device() -> str:
    return os.environ.get("WHISPERX_DEVICE", "cuda")


def align_languages() -> list[str]:
    """Languages `prefetch.py` downloads alignment models for."""
    return os.environ.get("ALIGN_LANGUAGES", "de en").split()


def hf_token() -> str | None:
    """Hugging Face token, needed for the gated diarization models only."""
    return os.environ.get("HF_TOKEN") or None


def resolve_media(path: str) -> Path | None:
    """Resolve `path` under `MEDIA_ROOT`; None if it escapes or is missing."""
    root = media_root()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate
