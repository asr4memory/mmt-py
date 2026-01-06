import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class FileInfo:
    """Class keeping track of file metadata."""

    def __init__(self, path: Path):
        self.path = path
        statinfo = os.stat(path)
        self.filename = path.name
        self.type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        self.size = statinfo.st_size
        self.modified = datetime.fromtimestamp(statinfo.st_mtime, tz=timezone.utc)

    @property
    def is_video(self) -> bool:
        return self.type.startswith('video')

    @property
    def is_audio(self) -> bool:
        return self.type.startswith('audio')


def get_files_with_info(dir_path: Path) -> list:
    dir_contents = get_dir_contents(dir_path)
    files_with_info = [FileInfo(filepath) for filepath in dir_contents]
    return files_with_info


def get_dir_contents(dir_path: Path) -> list:
    if not dir_path.is_dir():
        raise FileNotFoundError()

    dir_contents = [
        path
        for path in dir_path.iterdir()
        if path.is_file() and path.name != '.DS_Store'
    ]
    return dir_contents


def get_filename_suffix(date: datetime) -> str:
    return date.strftime('%Y%m%d%H%M%S')
