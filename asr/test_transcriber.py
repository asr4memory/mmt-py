"""whisperx is faked as a module: the tests never load a model or touch a GPU."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

whisperx = types.ModuleType("whisperx")
whisperx.load_audio = MagicMock()
whisperx.load_model = MagicMock()
whisperx.load_align_model = MagicMock()
whisperx.align = MagicMock()
whisperx.assign_word_speakers = MagicMock()
diarize_module = types.ModuleType("whisperx.diarize")
diarize_module.DiarizationPipeline = MagicMock()
sys.modules.setdefault("whisperx", whisperx)
sys.modules.setdefault("whisperx.diarize", diarize_module)

import transcriber  # noqa: E402

SEGMENTS = [{"start": 0.02, "end": 4.31, "text": "Guten Tag"}]
ALIGNED = {
    "segments": [
        {
            "start": 0.02,
            "end": 4.31,
            "text": "Guten Tag",
            "words": [{"word": "Guten", "start": 0.02, "end": 0.35, "score": 0.97}],
        }
    ],
    "word_segments": [{"word": "Guten"}],
}
DIARIZE_SEGMENTS = [{"start": 0.0, "end": 4.31, "speaker": "SPEAKER_00"}]
ASSIGNED = {
    "segments": [{**ALIGNED["segments"][0], "speaker": "SPEAKER_00"}],
    "word_segments": [{"word": "Guten", "speaker": "SPEAKER_00"}],
}


@pytest.fixture(autouse=True)
def whisperx_module(monkeypatch):
    """A fresh fake whisperx, and no leftover model singleton."""
    monkeypatch.setattr(transcriber, "_model", None)
    monkeypatch.setenv("WHISPERX_MODEL", "small")
    monkeypatch.setenv("WHISPERX_DEVICE", "cpu")
    monkeypatch.setenv("WHISPERX_COMPUTE_TYPE", "int8")
    monkeypatch.setenv("WHISPERX_BATCH_SIZE", "4")
    fake = transcriber.whisperx
    fake.load_audio = MagicMock(return_value="audio")
    fake.load_model = MagicMock(return_value=MagicMock())
    fake.load_align_model = MagicMock(return_value=("align-model", "metadata"))
    fake.align = MagicMock(return_value=dict(ALIGNED))
    fake.assign_word_speakers = MagicMock(return_value=dict(ASSIGNED))
    fake.load_model.return_value.transcribe = MagicMock(
        return_value={"language": "de", "segments": SEGMENTS}
    )
    pipeline = sys.modules["whisperx.diarize"].DiarizationPipeline
    pipeline.reset_mock()
    pipeline.return_value.return_value = DIARIZE_SEGMENTS
    return fake


@pytest.fixture
def pipeline():
    return sys.modules["whisperx.diarize"].DiarizationPipeline


def run(language=None, diarize=False, progress=None):
    return transcriber.transcribe(
        Path("/media/interview.mp4"), language, diarize, progress or (lambda value: None)
    )


def test_the_media_path_is_decoded_by_whisperx(whisperx_module):
    run()

    whisperx_module.load_audio.assert_called_once_with("/media/interview.mp4")


def test_the_model_is_loaded_from_the_environment_and_cached(whisperx_module):
    run()
    run()

    whisperx_module.load_model.assert_called_once_with(
        "small", "cpu", compute_type="int8"
    )


def test_an_explicit_language_is_passed_through(whisperx_module):
    run(language="de")

    kwargs = whisperx_module.load_model.return_value.transcribe.call_args.kwargs
    assert kwargs["language"] == "de"
    assert kwargs["batch_size"] == 4


def test_an_omitted_language_is_left_to_auto_detection(whisperx_module):
    result = run(language=None)

    kwargs = whisperx_module.load_model.return_value.transcribe.call_args.kwargs
    assert kwargs["language"] is None
    # The detected language drives alignment and is reported back.
    assert whisperx_module.load_align_model.call_args.kwargs["language_code"] == "de"
    assert result["language"] == "de"


def test_the_aligned_output_is_returned_unmodified(whisperx_module):
    result = run(language="de")

    assert result["segments"] == ALIGNED["segments"]
    assert result["word_segments"] == ALIGNED["word_segments"]
    assert result == {**ALIGNED, "language": "de"}


def test_the_transcribed_segments_are_handed_to_align(whisperx_module):
    run()

    args = whisperx_module.align.call_args.args
    assert args[0] is SEGMENTS
    assert args[1] == "align-model"
    assert args[2] == "metadata"
    assert args[3] == "audio"


def test_progress_moves_through_the_stage_bands_in_order(whisperx_module):
    def transcribe(audio, **kwargs):
        print("Progress: 50.00%...")
        print("Progress: 100.00%...")
        return {"language": "de", "segments": SEGMENTS}

    def align(*args, **kwargs):
        print("Detected language: de")
        print("Progress: 100.00%...")
        return dict(ALIGNED)

    whisperx_module.load_model.return_value.transcribe = transcribe
    whisperx_module.align = align
    seen = []

    run(progress=seen.append)

    assert seen == pytest.approx([0.0, 0.35, 0.7, 0.7, 0.95, 0.95])
    assert seen == sorted(seen)


def test_whisperx_progress_output_is_not_printed(whisperx_module, capsys):
    def transcribe(audio, **kwargs):
        print("Progress: 50.00%...")
        return {"language": "de", "segments": SEGMENTS}

    whisperx_module.load_model.return_value.transcribe = transcribe

    run()

    assert "Progress" not in capsys.readouterr().out


def test_diarization_assigns_speakers_to_words(whisperx_module, pipeline, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_secret")

    result = run(diarize=True)

    pipeline.assert_called_once_with(
        "pyannote/speaker-diarization-community-1", token="hf_secret", device="cpu"
    )
    pipeline.return_value.assert_called_once_with("audio")
    args = whisperx_module.assign_word_speakers.call_args.args
    assert args[0] is DIARIZE_SEGMENTS
    assert args[1] == ALIGNED
    assert result == {**ASSIGNED, "language": "de"}


def test_diarization_progress_uses_the_diarize_bands(whisperx_module, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_secret")

    def transcribe(audio, **kwargs):
        print("Progress: 50.00%...")
        print("Progress: 100.00%...")
        return {"language": "de", "segments": SEGMENTS}

    def align(*args, **kwargs):
        print("Progress: 100.00%...")
        return dict(ALIGNED)

    whisperx_module.load_model.return_value.transcribe = transcribe
    whisperx_module.align = align
    seen = []

    run(diarize=True, progress=seen.append)

    assert seen == pytest.approx([0.0, 0.3, 0.6, 0.6, 0.8, 0.8, 0.95])
    assert seen == sorted(seen)


def test_diarization_without_a_token_fails_the_job(whisperx_module, pipeline, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)

    with pytest.raises(RuntimeError):
        run(diarize=True)

    pipeline.assert_not_called()
