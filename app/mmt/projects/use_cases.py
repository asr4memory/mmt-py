import logging
from pathlib import Path
from typing import Optional

from django.core.exceptions import ValidationError

from mmt.projects.models import Project


def create_project(**kwargs) -> tuple[bool, Optional[Project]]:
    """
    Create a project using (form) data and a user object.
    Also creates all project directories in the process.
    Returns a tuple with a success boolean and the project, if it was created.
    """
    try:
        project = Project.objects.create(**kwargs)

        project.upload_directory.mkdir(parents=True, exist_ok=True)
        project.download_directory.mkdir(parents=True, exist_ok=True)

        return (True, project)
    except Exception as e:
        return (False, None)


def update_project(project: Project, title: str, description: str) -> bool:
    """
    Update the project.
    Also rename the project directory if necessary.
    If this fails, the whole update should fail.
    """
    old_project_dir = project.project_directory

    project.title = title
    project.description = description

    # Validate new values.
    try:
        project.clean_fields()
    except ValidationError:
        project.refresh_from_db()
        return False

    # Rename project directory if necessary.
    try:
        if project.project_directory != old_project_dir:
            rename_directory(old_project_dir, project.project_directory)
    except:
        project.refresh_from_db()
        return False

    # If all went well, save project.
    project.save()
    return True


def rename_directory(old_path: Path, new_path: Path):
    old_path.rename(new_path)


def delete_project(project: Project) -> bool:
    """
    Deletes the project and the project directories.
    If the project directories cannot be deleted, the project will
    also be not deleted from the database.
    """
    if delete_project_directory(project):
        project.delete()
        return True
    else:
        return False


def delete_project_directory(project: Project) -> bool:
    try:
        remove_dir_and_files(project.upload_directory)
        remove_dir_and_files(project.download_directory)
        remove_dir_and_files(project.project_directory)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        logging.error('Failed to delete %s: %s', project.project_directory, e)
        return False


def remove_dir_and_files(dir: Path) -> None:
    if dir.is_dir():
        for path in dir.iterdir():
            path.unlink(missing_ok=True)
        dir.rmdir()
