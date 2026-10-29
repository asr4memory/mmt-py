"""The only module that imports whisperx.

Returns whisperx's aligned output as-is (plus the detected `language` and the
`model` it ran with); the app owns the conversion to the mmt transcript format.
"""

import gc
import io
from collections.abc import Callable
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

import whisperx

import config
from models import ModelSpec
from prefetch import DIARIZATION_MODEL
from progress import parse_progress_line, stage_fraction

Transcribe = Callable[
    [Path, ModelSpec, str | None, bool, Callable[[float], None]], dict
]

# Service-internal tuning, deliberately not exposed per job.
CHUNK_SIZE = 30

# One loaded model per process (one GPU), together with its registry name.
_model = None
_model_name: str | None = None


def get_model(spec: ModelSpec):
    """The whisper model for `spec`; a different loaded model is released first."""
    global _model, _model_name
    if _model is not None and _model_name == spec.name:
        return _model
    if _model is not None:
        _model = None
        _model_name = None
        gc.collect()
        if config.whisperx_device() == "cuda":
            import torch

            torch.cuda.empty_cache()
    _model = whisperx.load_model(
        spec.source, config.whisperx_device(), compute_type=spec.compute_type
    )
    _model_name = spec.name
    return _model


class _ProgressLines(io.TextIOBase):
    """Turns whisperx's printed `Progress: NN.NN%...` lines into callbacks."""

    def __init__(self, stage: str, diarize: bool, progress: Callable[[float], None]):
        self.stage = stage
        self.diarize = diarize
        self.progress = progress
        self.buffer = ""

    def write(self, text: str) -> int:
        self.buffer += text
        while "\n" in self.buffer:
            line, _, self.buffer = self.buffer.partition("\n")
            within = parse_progress_line(line)
            if within is not None:
                self.progress(stage_fraction(self.stage, within, self.diarize))
        return len(text)


@contextmanager
def _stage(stage: str, diarize: bool, progress: Callable[[float], None]):
    """Report the stage boundary, then whatever whisperx prints inside it."""
    progress(stage_fraction(stage, 0.0, diarize))
    with redirect_stdout(_ProgressLines(stage, diarize, progress)):
        yield


def transcribe(
    media: Path,
    spec: ModelSpec,
    language: str | None,
    diarize: bool,
    progress: Callable[[float], None],
) -> dict:
    # Read the token up front so a diarization job without one fails before any
    # transcription work runs, rather than after it.
    token = config.hf_token() if diarize else None
    if diarize and token is None:
        raise RuntimeError("HF_TOKEN is required for diarization")

    device = config.whisperx_device()
    audio = whisperx.load_audio(str(media))

    with _stage("transcribe", diarize, progress):
        result = get_model(spec).transcribe(
            audio,
            batch_size=spec.batch_size,
            language=language,
            chunk_size=CHUNK_SIZE,
            print_progress=True,
        )

    detected = result["language"]
    align_model, metadata = whisperx.load_align_model(
        language_code=detected, device=device
    )
    with _stage("align", diarize, progress):
        aligned = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
            print_progress=True,
        )

    if diarize:
        aligned = _diarize(audio, aligned, device, token, progress)

    progress(stage_fraction("finalize", 0.0, diarize))
    return {**aligned, "language": detected, "model": spec.name}


def _diarize(
    audio,
    aligned: dict,
    device: str,
    token: str,
    progress: Callable[[float], None],
) -> dict:
    """Run the pyannote pipeline and attach a speaker to each word."""
    from whisperx.diarize import DiarizationPipeline

    with _stage("diarize", True, progress):
        pipeline = DiarizationPipeline(DIARIZATION_MODEL, token=token, device=device)
        diarize_segments = pipeline(audio)
    return whisperx.assign_word_speakers(diarize_segments, aligned)
