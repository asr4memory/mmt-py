from pathlib import Path

from django.db import models
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import Project


class UploadedFile(models.Model):
    class UploadStatus(models.TextChoices):
        CREATED = "created", _("Created")  # Metadata exists, no file yet
        UPLOADING = "uploading", _("Uploading")  # File is being uploaded
        COMPLETE = "complete", _("Complete")  # Upload finished successfully
        CORRUPT = "corrupt", _("Corrupt")  # File uploaded but failed integrity checks
        MISSING = "missing", _("Missing")  # No file found on disk

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="uploaded_files",
        verbose_name=_("Project"),
    )
    filename = models.CharField(max_length=255, verbose_name=_("Filename"))
    size = models.BigIntegerField(default=0, verbose_name=_("Size"))
    transferred = models.BigIntegerField(default=0, verbose_name=_("Transferred"))
    status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.CREATED,
        verbose_name=_("Status"),
    )
    media_type = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_("Media type")
    )
    checksum_server = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_("Server checksum")
    )
    checksum_client = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_("Client checksum")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["created_at", "filename"]
        verbose_name = _("uploaded file")
        verbose_name_plural = _("uploaded files")

    @property
    def file_path(self) -> Path:
        return self.project.directory_path / self.filename

    @property
    async def afile_path(self) -> Path:
        "Async version of file_path"
        project = await Project.objects.aget(pk=self.project_id)
        project_path = await project.adirectory_path
        return project_path / self.filename

    def delete_file(self) -> None:
        "Remove actual file. Call before deleting record."
        try:
            self.file_path.unlink()
        except FileNotFoundError:
            print(f"File {self.filename} does not exist.")

    def __str__(self):
        return self.filename
