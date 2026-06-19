import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from mmt.projects.exceptions import ProjectError, ProjectPathError
from mmt.projects.models import Project


def create_project(*, title: str, user, description: str = '') -> Project:
    """
    Create a project and its upload/download directories.

    The database row and the directories are created together: if directory
    creation fails, the row is rolled back and the underlying exception
    propagates.
    """
    with transaction.atomic():
        project = Project.objects.create(
            title=title, description=description, user=user
        )

        project.ensure_directories()

    return project


def update_project_title(project: Project, title: str) -> None:
    """
    Apply a new title to the project, validating it and renaming the project
    directory if the title changed, then persist the project.

    Any other pending changes on the project (e.g. a new description set by the
    caller) are saved along with the title.

    Raises ValidationError if the title is invalid and ProjectError if the
    directory rename fails. In either case the in-memory project is restored
    from the database and nothing is saved.
    """
    old_project_dir = project.project_directory

    project.title = title

    # Validate the new title.
    try:
        project.clean_fields()
    except ValidationError:
        project.refresh_from_db()
        raise

    # Rename project directory if necessary.
    try:
        if project.project_directory != old_project_dir:
            rename_directory(old_project_dir, project.project_directory)
    except Exception as e:
        project.refresh_from_db()
        raise ProjectError('Failed to rename project directory') from e

    project.save()


def rename_directory(old_path: Path, new_path: Path):
    old_path.rename(new_path)


def delete_project(project: Project) -> None:
    """
    Delete the project from the database, then remove its directories.

    Raises ProjectPathError if the project directory escapes the user files
    directory; in that case nothing is deleted.

    If the database deletion fails, the underlying exception propagates and
    nothing is changed.

    If directory cleanup fails after a successful DB deletion, the error is
    logged but no exception is raised — orphaned files are an admin concern,
    not a reason to fail the operation.
    """
    project_directory = project.project_directory
    if not project_directory.resolve().is_relative_to(
        settings.MMT_USER_FILES_DIR.resolve()
    ):
        raise ProjectPathError(
            f'Refusing to delete {project_directory}: path escapes user files directory'
        )

    project.delete()

    try:
        shutil.rmtree(project_directory)
    except FileNotFoundError:
        pass
    except Exception:
        logging.exception(f'Failed to delete directory {project_directory}')
