"""Detection and classification of MIME types."""

import mimetypes
from enum import StrEnum
from pathlib import Path

import magic

UNKNOWN = 'application/octet-stream'


class Category(StrEnum):
    VIDEO = 'video'
    AUDIO = 'audio'
    PDF = 'pdf'
    IMAGE = 'image'
    TEXT = 'text'
    OTHER = 'other'


def detect(path: Path, default: str = UNKNOWN) -> str:
    """Return the MIME type of the file at path.

    The type is detected from the file's contents. If the file cannot be read
    or its contents are not recognised, the type is guessed from the file
    extension, and if the extension is unknown, default is returned. The
    function does not raise an exception.

    The contents take precedence because types derived from the filename are
    unreliable: browsers report ``application/ogg`` for any .ogg file, and
    ``mimetypes`` reports ``audio/ogg`` for the same extension.
    """
    try:
        type_from_contents = magic.from_file(str(path), mime=True)
    except magic.MagicException, OSError:
        type_from_contents = UNKNOWN
    # libmagic reports application/octet-stream for contents it does not
    # recognise.
    if type_from_contents != UNKNOWN:
        return type_from_contents

    type_from_extension, _encoding = mimetypes.guess_type(path)
    return type_from_extension or default


def category(media_type: str) -> Category:
    """Map a MIME type to a broad category."""
    if media_type.startswith('video') or media_type in (
        'application/ogg',
        'application/mxf',
    ):
        return Category.VIDEO
    if media_type.startswith('audio'):
        return Category.AUDIO
    if media_type == 'application/pdf':
        return Category.PDF
    if media_type.startswith('image/'):
        return Category.IMAGE
    if media_type.startswith('text/'):
        return Category.TEXT
    return Category.OTHER
