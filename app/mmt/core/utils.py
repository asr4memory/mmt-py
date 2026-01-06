import unicodedata

KEEP_CHARACTERS = (' ', '.', '_')


def to_ascii(s: str) -> str:
    "Normalize to NFKD, drop non-ASCII"
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def filename_safe(text: str) -> str:
    assert isinstance(text, str)

    result = to_ascii(text)
    result = (
        ''.join(c for c in result if c.isalnum() or c in KEEP_CHARACTERS)
        .rstrip()
        .replace(' ', '_')
        .lower()
    )

    return result
