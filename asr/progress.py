"""Mapping whisperx's printed progress onto a single [0, 1] fraction.

Pure: no I/O, no whisperx import. whisperx exposes intra-stage progress
only by printing ``Progress: NN.NN%...`` per segment, so the worker
captures stdout and feeds the lines through here.
"""

import re

_PROGRESS_LINE = re.compile(r"^\s*Progress:\s*(\d+(?:\.\d+)?)%")

# stage -> (start, end) of the stage's band, keyed by whether diarization runs.
_BANDS = {
    False: {
        "transcribe": (0.00, 0.70),
        "align": (0.70, 0.95),
        "finalize": (0.95, 1.00),
    },
    True: {
        "transcribe": (0.00, 0.60),
        "align": (0.60, 0.80),
        "diarize": (0.80, 0.95),
        "finalize": (0.95, 1.00),
    },
}


def parse_progress_line(line: str) -> float | None:
    """Return the fraction in a whisperx progress line, or None."""
    match = _PROGRESS_LINE.match(line)
    if match is None:
        return None
    return float(match.group(1)) / 100


def stage_fraction(stage: str, within: float, diarize: bool) -> float:
    """Map progress `within` a stage onto the overall [0, 1] fraction."""
    bands = _BANDS[diarize]
    if stage not in bands:
        raise ValueError(f"unknown stage: {stage}")
    start, end = bands[stage]
    within = min(1.0, max(0.0, within))
    return start + within * (end - start)
