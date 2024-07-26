import os
from pathlib import Path


def create_user_directories(username: str) -> None:
    root_path = Path(__file__).parent.parent
    user_files_path = root_path / "user_files"

    user_directory = user_files_path / username
    user_directory.mkdir(exist_ok=True)

    uploads_directory = user_directory / "uploads"
    downloads_directory = user_directory / "downloads"
    uploads_directory.mkdir(exist_ok=True)
    downloads_directory.mkdir(exist_ok=True)
