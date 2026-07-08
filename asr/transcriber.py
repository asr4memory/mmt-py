"""The only module that imports whisperx.

Returns whisperx's aligned output as-is (plus the detected `language`); the
app owns the conversion to the mmt transcript format.
"""

import io
from collections.abc import Callable
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

import whisperx

import config
from progress import parse_progress_line, stage_fraction

Transcribe = Callable[[Path, str | None, bool, Callable[[float], None]], dict]

# Service-internal tuning, deliberately not exposed per job.
CHUNK_SIZE = 30

_model = None


def get_model():
    """The whisper model, loaded once per process (one GPU, one instance)."""
    global _model
    if _model is None:
        _model = whisperx.load_model(
            config.whisperx_model(),
            config.whisperx_device(),
            compute_type=config.whisperx_compute_type(),
        )
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
    language: str | None,
    diarize: bool,
    progress: Callable[[float], None],
) -> dict:
    if diarize:
        raise NotImplementedError("diarization")

    device = config.whisperx_device()
    audio = whisperx.load_audio(str(media))

    with _stage("transcribe", diarize, progress):
        result = get_model().transcribe(
            audio,
            batch_size=config.whisperx_batch_size(),
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

    progress(stage_fraction("finalize", 0.0, diarize))
    return {**aligned, "language": detected}
