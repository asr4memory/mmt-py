"""Timecode arithmetic shared by the subtitle formats."""


def hhmmssmmm(seconds: float, *, millisecond_separator: str = '.') -> str:
    """Format seconds as HH:MM:SS.mmm.

    Hours are not truncated at 24 and are always at least two digits.
    Milliseconds are truncated, not rounded, so that a cue never ends after
    the next one starts because of rounding.
    """
    total_milliseconds = int(seconds * 1000)
    milliseconds = total_milliseconds % 1000
    total_seconds = total_milliseconds // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)

    return (
        f'{hours:02d}:{minutes:02d}:{whole_seconds:02d}'
        f'{millisecond_separator}{milliseconds:03d}'
    )
