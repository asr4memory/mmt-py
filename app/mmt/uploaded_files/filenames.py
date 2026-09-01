"""Shaping the name an uploaded file is stored under."""

import re
from pathlib import PurePosixPath

from anyascii import anyascii

# anyascii emits ASCII, but not only the characters a stored name may use: it
# writes an apostrophe in a Cyrillic romanisation (Интервью -> Interv'yu) and
# wraps an emoji in colons (😀 -> :grinning:).
DISALLOWED_RE = re.compile(r'[^a-z0-9._-]')
UNDERSCORE_RUN_RE = re.compile(r'_+')


def fit_filename(name: str, limit: int = 200) -> str:
    """Shorten a filename so that it fits the filesystem's limit for one path
    component, keeping its extension.

    NAME_MAX is 255 bytes on Linux, so the limit counts bytes and not
    characters: a name of 255 characters with umlauts does not fit. The default
    of 200 leaves room for what the application appends to a stored name later,
    the duplicate suffix and the ``.mp4`` of the web version.

    If uploads ever move to a FileField with a storage backend, its
    ``get_available_name`` takes over the uniqueness suffix and the shortening.
    It truncates by characters against the column length rather than by bytes,
    so the byte rule here is still needed on top of it.
    """
    if len(name.encode('utf-8')) <= limit:
        return name

    # PurePosixPath rather than str.rpartition, which reads a dotfile's leading
    # dot as the start of an extension.
    parts = PurePosixPath(name)
    stem = parts.stem
    suffix = parts.suffix
    budget = limit - len(suffix.encode('utf-8'))
    if budget <= 0:
        # The name is one long extension, so there is no stem to shorten.
        stem = name
        suffix = ''
        budget = limit

    # A slice by bytes can end inside a multi-byte character, which 'ignore'
    # then drops.
    return stem.encode('utf-8')[:budget].decode('utf-8', 'ignore') + suffix


def storage_filename(name: str, limit: int = 200) -> str:
    """Shape a submitted filename into the name the file is stored under.

    The result is a non-empty ASCII name matching ``[a-z0-9._-]+`` that neither
    starts nor ends with a dot, a dash or an underscore: a leading dot hides
    the file from a directory listing and a leading dash is read as an option
    by command line tools such as ffmpeg.

    The extension is split off first and each part is transliterated on its
    own, so a name whose stem transliterates to nothing is detected as such and
    falls back to ``file``. The byte limit is applied last, because a
    romanisation can be longer than the name it came from.
    """
    parts = PurePosixPath(name)
    stem = _to_ascii(parts.stem).strip('.-_')
    suffix = _to_ascii(parts.suffix)
    if not stem:
        stem = 'file'

    return fit_filename(stem + suffix, limit=limit)


def _to_ascii(part: str) -> str:
    """Transliterate one part of a filename and reduce it to the allowed set."""
    # anyascii preserves case, and the allowed set holds no uppercase letters,
    # so lowercasing has to happen before the set is applied: a capital that
    # survives it is deleted rather than folded.
    part = anyascii(part).lower().replace(' ', '_')
    part = DISALLOWED_RE.sub('', part)
    return UNDERSCORE_RUN_RE.sub('_', part)
