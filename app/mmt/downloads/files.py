from datetime import datetime, timezone
import mimetypes
import os
from pathlib import Path


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
        media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        statinfo = os.stat(filepath)
        file_info = {
            "filename": filepath.name,
            "type": media_type,
            "size": statinfo.st_size,
            "modified": datetime.fromtimestamp(statinfo.st_mtime, tz=timezone.utc),
        }
        files_with_info.append(file_info)

    return files_with_info
