from django.db import models
from django.utils.translation import gettext_lazy as _


class UploadedFile(models.Model):
    class UploadStatus(models.TextChoices):
        CREATED = "created", _("Created")  # Metadata exists, no file yet
        UPLOADING = "uploading", _("Uploading")  # File is being uploaded
        COMPLETE = "complete", _("Complete")  # Upload finished successfully
        CORRUPT = "corrupt", _("Corrupt")  # File uploaded but failed integrity checks
        MISSING = "missing", _("Missing")  # No file found on disk

    upload_job = models.ForeignKey(
        "upload_jobs.UploadJob",
        on_delete=models.CASCADE,
        related_name="uploaded_files",
        verbose_name=_("Upload job"),
    )
    filename = models.CharField(max_length=255, verbose_name=_("Filename"))
    size = models.BigIntegerField(default=0, verbose_name=_("Size"))
    chunk_count = models.IntegerField(default=1, verbose_name=_("Chunk count"))
    chunks_transferred = models.IntegerField(
        default=0, verbose_name=_("Chunks transferred")
    )
    status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.CREATED,
        verbose_name=_("Status"),
    )
    transferred = models.BigIntegerField(default=0, verbose_name=_("Transferred"))
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

    def __str__(self):
        return self.filename
