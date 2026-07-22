"""whisperx is faked as a module: the tests never download a model."""

import sys
import types
from unittest.mock import MagicMock

import pytest

whisperx = types.ModuleType("whisperx")
whisperx.load_model = MagicMock()
whisperx.load_align_model = MagicMock()
diarize_module = types.ModuleType("whisperx.diarize")
diarize_module.DiarizationPipeline = MagicMock()
sys.modules.setdefault("whisperx", whisperx)
sys.modules.setdefault("whisperx.diarize", diarize_module)

import prefetch  # noqa: E402


@pytest.fixture(autouse=True)
def whisperx_module(monkeypatch):
    """A fresh fake whisperx and a fresh fake diarization pipeline."""
    fake = prefetch.whisperx
    fake.load_model = MagicMock()
    fake.load_align_model = MagicMock(return_value=("align-model", "metadata"))
    pipeline = sys.modules["whisperx.diarize"]
    pipeline.DiarizationPipeline = MagicMock()
    return fake


@pytest.fixture
def pipeline():
    return sys.modules["whisperx.diarize"].DiarizationPipeline


def test_prefetch_loads_the_configured_model_on_the_cpu(whisperx_module):
    prefetch.prefetch("large-v3", [], None)

    whisperx_module.load_model.assert_called_once_with(
        "large-v3", "cpu", compute_type="int8"
    )


def test_prefetch_loads_an_align_model_per_language(whisperx_module):
    prefetch.prefetch("small", ["de", "en"], None)

    assert [
        call.kwargs["language_code"]
        for call in whisperx_module.load_align_model.call_args_list
    ] == ["de", "en"]
    for call in whisperx_module.load_align_model.call_args_list:
        assert call.kwargs["device"] == "cpu"


def test_prefetch_skips_diarization_without_a_token(pipeline):
    prefetch.prefetch("small", ["de"], None)

    pipeline.assert_not_called()


def test_prefetch_loads_the_diarization_pipeline_with_a_token(pipeline):
    prefetch.prefetch("small", ["de"], "hf_secret")

    # whisperx 3.8 names the parameter `token`; `use_auth_token` was removed.
    # The model is named explicitly rather than left to whisperx's default.
    pipeline.assert_called_once_with(
        "pyannote/speaker-diarization-community-1", token="hf_secret", device="cpu"
    )


def test_main_reads_the_environment(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(prefetch, "prefetch", called)

    monkeypatch.setenv("WHISPERX_MODEL", "medium")
    monkeypatch.setenv("ALIGN_LANGUAGES", "de en fr")
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    prefetch.main()

    called.assert_called_once_with("medium", ["de", "en", "fr"], "hf_secret")

    called.reset_mock()
    # raising=False: the dev machine exports these, a CI runner does not.
    monkeypatch.delenv("WHISPERX_MODEL", raising=False)
    monkeypatch.delenv("ALIGN_LANGUAGES", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    prefetch.main()

    called.assert_called_once_with("large-v3", ["de", "en"], None)
