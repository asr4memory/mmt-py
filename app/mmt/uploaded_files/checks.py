from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileIssue:
    """A single problem found when checking an uploaded file against disk.

    Admin-facing; messages are plain English (not translated).
    """

    code: str
    message: str


@dataclass
class FileCheckResult:
    """Structured report returned by :meth:`UploadedFile.check_file`."""

    issues: list[FileIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues
