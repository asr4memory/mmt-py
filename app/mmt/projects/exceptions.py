class ProjectError(Exception):
    """Base class for project use-case failures."""


class ProjectPathError(ProjectError):
    """The project's directory falls outside the user files dir — refuse to touch it."""
