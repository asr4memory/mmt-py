from dataclasses import dataclass, field


@dataclass(frozen=True)
class DirectoryIssue:
    """A single problem found when checking a project's directories.

    Admin-facing; messages are plain English (not translated).
    """

    directory: str  # "project" | "upload" | "download"
    code: str  # "missing" | "stat_error" | "not_a_directory" | "not_readable" | ...
    message: str


@dataclass
class ProjectCheckResult:
    """Structured report returned by :meth:`Project.check_directories`."""

    issues: list[DirectoryIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues
