import pytest

from progress import parse_progress_line, stage_fraction


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Progress: 34.52%...", 0.3452),
        ("Progress: 0.00%...", 0.0),
        ("Progress: 100.00%...", 1.0),
        ("Progress: 7%...", 0.07),
        ("  Progress: 12.50%...\n", 0.125),
    ],
)
def test_parse_progress_line_reads_whisperx_output(line, expected):
    assert parse_progress_line(line) == pytest.approx(expected)


@pytest.mark.parametrize(
    "line",
    [
        "",
        "\n",
        "Detected language: de",
        "Progress: unknown",
        "progress: 10.00%...",
        "no percentage here 50",
        "Progress: %...",
    ],
)
def test_parse_progress_line_ignores_anything_else(line):
    assert parse_progress_line(line) is None


def test_bands_without_diarization():
    assert stage_fraction("transcribe", 0.0, False) == pytest.approx(0.0)
    assert stage_fraction("transcribe", 1.0, False) == pytest.approx(0.7)
    assert stage_fraction("align", 0.0, False) == pytest.approx(0.7)
    assert stage_fraction("align", 1.0, False) == pytest.approx(0.95)
    assert stage_fraction("finalize", 0.0, False) == pytest.approx(0.95)
    assert stage_fraction("finalize", 1.0, False) == pytest.approx(1.0)


def test_bands_with_diarization():
    assert stage_fraction("transcribe", 1.0, True) == pytest.approx(0.6)
    assert stage_fraction("align", 0.0, True) == pytest.approx(0.6)
    assert stage_fraction("align", 1.0, True) == pytest.approx(0.8)
    assert stage_fraction("diarize", 0.0, True) == pytest.approx(0.8)
    assert stage_fraction("diarize", 1.0, True) == pytest.approx(0.95)
    assert stage_fraction("finalize", 0.0, True) == pytest.approx(0.95)
    assert stage_fraction("finalize", 1.0, True) == pytest.approx(1.0)


def test_within_maps_linearly_into_the_band():
    assert stage_fraction("transcribe", 0.5, False) == pytest.approx(0.35)
    assert stage_fraction("align", 0.5, False) == pytest.approx(0.825)


def test_within_is_clamped():
    assert stage_fraction("transcribe", -1.0, False) == pytest.approx(0.0)
    assert stage_fraction("transcribe", 2.0, False) == pytest.approx(0.7)


def test_diarize_stage_is_unavailable_without_diarization():
    with pytest.raises(ValueError):
        stage_fraction("diarize", 0.5, False)


def test_unknown_stage_raises():
    with pytest.raises(ValueError):
        stage_fraction("nonsense", 0.5, False)
