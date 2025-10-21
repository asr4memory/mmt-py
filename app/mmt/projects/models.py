import logging
from pathlib import Path
import shutil

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from mmt.core.utils import filename_safe
from mmt.projects.utils import get_filename_suffix

User = get_user_model()


class Project(models.Model):
    title = models.CharField(max_length=128, verbose_name=_("Title"))
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
    downloadable_files_count = models.IntegerField(
        default=0,
        verbose_name=_("Downloadable files count"),
        help_text=_("Cache field for number of files in download directory."),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("project")
        verbose_name_plural = _("projects")

    @property
    def directory_name(self) -> str:
        safe_name = filename_safe(self.title)
        date_suffix = get_filename_suffix(self.created_at)
        return f"{safe_name}.{date_suffix}"

    @property
    def project_directory(self) -> Path:
        return self.user.user_directory / self.directory_name

    @property
    def upload_directory(self) -> Path:
        return self.project_directory / "upload"

    @property
    def download_directory(self) -> Path:
        return self.project_directory / "download"

    @property
    async def aproject_directory(self) -> Path:
        "Async version of project_directory"
        user = await User.objects.aget(pk=self.user_id)
        result = user.user_directory / self.directory_name
        return result

    @property
    async def aupload_directory(self) -> Path:
        project_directory = await self.aproject_directory
        return project_directory / "upload"

    def make_project_directories(self) -> Path:
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        self.download_directory.mkdir(parents=True, exist_ok=True)
        return self.project_directory

    def rename_directory_from(self, old_path: Path) -> Path:
        result = old_path.rename(self.project_directory)
        return result

    def remove_project_directories(self) -> bool:
        """
        Deletes the project directory including its subdirectories.
        Returns True if deletion succeeded, False if directory does not exist.
        """
        try:
            shutil.rmtree(self.project_directory)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logging.error("Failed to delete %s: %s", self.project_directory, e)
            return False

    def __str__(self):
        return f"{self.title}"


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
    uploaded_files = models.JSONField(default=list, verbose_name=_("Uploaded files"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("processing request")
        verbose_name_plural = _("processing requests")

    def __str__(self):
        return f"{self.project.title} {self.created_at}"
