import logging
import shutil
from pathlib import Path
from typing import Optional

from django.conf import settings
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
        logging.error(f'Failed to create project: {e}')
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
    Deletes the project from the database and then removes its directories.
    If the database deletion fails, nothing is changed.
    If directory cleanup fails after a successful DB deletion, the error is
    logged but True is still returned — orphaned files are an admin concern,
    not a reason to leave the user with a broken project.
    """
    project_directory = project.project_directory
    if not project_directory.resolve().is_relative_to(settings.MMT_USER_FILES_DIR.resolve()):
        logging.error(f'Refusing to delete {project_directory}: path escapes user files directory')
        return False

    try:
        project.delete()
    except Exception as e:
        logging.error(f'Failed to delete project {project.pk} from database: {e}')
        return False

    try:
        shutil.rmtree(project_directory)
    except FileNotFoundError:
        pass
    except Exception as e:
        logging.error(f'Failed to delete directory {project_directory}: {e}')

    return True
