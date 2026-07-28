import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path

from mmt.core.utils import file_category


class FileInfo:
    """Class keeping track of file metadata."""

    def __init__(self, path: Path):
        self.path = path
        statinfo = os.stat(path)
        self.filename = path.name
        self.type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        self.size = statinfo.st_size
        self.modified = datetime.fromtimestamp(statinfo.st_mtime, tz=UTC)

    def file_category(self) -> str:
        return file_category(self.type)

    @property
    def is_video(self) -> bool:
        return self.file_category() == 'video'

    @property
    def is_audio(self) -> bool:
        return self.file_category() == 'audio'


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
    return sorted(dir_contents, key=lambda path: path.name.lower())


def get_filename_suffix(date: datetime) -> str:
    return date.strftime('%Y%m%d%H%M%S')
