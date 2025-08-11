from pathlib import Path

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .utils import filename_safe


class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        related_query_name="project",
        verbose_name="User",
    )
    description = models.TextField(
        blank=True, default="", verbose_name=_("Description")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("project")
        verbose_name_plural = _("projects")

    @property
    def directory_name(self) -> str:
        safe_name = filename_safe(self.name)
        date_suffix = self.created_at.strftime(".%Y-%m-%dT%H%M%SZ")
        return safe_name + date_suffix

    @property
    def directory_path(self) -> Path:
        uploads_directory = self.user.upload_path
        result = uploads_directory / self.directory_name
        return result

    def create_directory(self) -> Path:
        self.directory_path.mkdir(parents=True, exist_ok=True)
        return self.directory_path

    def rename_directory_from(self, old_path: Path) -> Path:
        result = old_path.rename(self.directory_path)
        return result

    def __str__(self):
        return f"{self.name}"


class ProcessingRequest(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", _("Created")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")
        COMPLETED = "completed", _("Completed")

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="processing_requests",
        related_query_name="processing_request",
        verbose_name="Project",
    )
    description = models.TextField(
        blank=True, default="", verbose_name=_("Description")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name=_("Status"),
    )
    admin_comment = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Admin comment"),
        help_text=_("Optional comment by the administrator reviewing this request."),
    )
    language = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Language")
    )
    make_available_on_platform = models.BooleanField(
        default=False, verbose_name=_("Make available on platform")
    )
    transcribe = models.BooleanField(default=False, verbose_name=_("Transcribe"))
    check_media_files = models.BooleanField(
        default=False, verbose_name=_("Check media files")
    )
    replace_existing_files = models.BooleanField(
        default=False, verbose_name=_("Replace existing files")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("processing request")
        verbose_name_plural = _("processing requests")

    def __str__(self):
        return f"{self.project.name} {self.created_at}"
