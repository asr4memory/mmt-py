from decimal import Decimal


def hhmmssmmm(seconds: float, *, millisecond_separator: str = '.') -> str:
    """Format seconds as HH:MM:SS.mmm.

    Milliseconds are truncated, not rounded, so that a cue never ends after the
    next one starts because of rounding. The value is converted through
    ``Decimal(str(seconds))`` rather than by multiplying the float, because
    ``0.3 * 1000`` is 299.99999999999994 in binary floating point and would
    truncate to 299 milliseconds.

    Hours are not truncated at 24 and are always at least two digits.
    """
    total_milliseconds = int(Decimal(str(seconds)) * 1000)
    whole_seconds, milliseconds = divmod(total_milliseconds, 1000)
    total_minutes, second = divmod(whole_seconds, 60)
    hour, minute = divmod(total_minutes, 60)
    return (
        f'{hour:02d}:{minute:02d}:{second:02d}{millisecond_separator}{milliseconds:03d}'
    )
