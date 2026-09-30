import hashlib
import unicodedata
from pathlib import Path


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
        .strip('.')
    )

    if not result:
        raise ValueError(f'filename_safe: {text!r} produced an empty string')

    return result


def file_data(file_path, chunk_size=65536):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk


def generate_file_md5(path: Path, block_size=2**20) -> str:
    m = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(block_size)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def format_duration(duration: float) -> str:
    """Formats media duration"""
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    secs = int(duration % 60)
    if hours > 0:
        return f'{hours}h{minutes}m{secs}s'
    else:
        return f'{minutes}m{secs}s'
