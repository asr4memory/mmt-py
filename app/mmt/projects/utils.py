from dataclasses import dataclass
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FileInfo:
    """Class keeping track of file metadata."""

    path: Path
    filename: str
    type: str
    size: int
    modified: datetime

    def is_video(self) -> bool:
        return self.type.startswith("video")

    def is_audio(self) -> bool:
        return self.type.startswith("audio")


def get_files_with_info(dir_path: Path) -> list:
    if not dir_path.is_dir():
        raise FileNotFoundError()

    filepaths = [
        path
        for path in dir_path.iterdir()
        if path.is_file() and path.name != ".DS_Store"
    ]

    files_with_info = []
    for filepath in filepaths:
        file_info = get_file_info(filepath)
        files_with_info.append(file_info)

    return files_with_info


def get_file_info(filepath: Path) -> FileInfo:
    media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    statinfo = os.stat(filepath)
    file_info = FileInfo(
        path=Path,
        filename=filepath.name,
        type=media_type,
        size=statinfo.st_size,
        modified=datetime.fromtimestamp(statinfo.st_mtime, tz=timezone.utc),
    )
    return file_info


def get_filename_suffix(date: datetime) -> str:
    return date.strftime("%Y%m%d%H%M%S")
