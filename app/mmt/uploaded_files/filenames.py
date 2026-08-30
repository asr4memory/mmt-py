"""Shaping the name an uploaded file is stored under."""

from pathlib import PurePosixPath


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
