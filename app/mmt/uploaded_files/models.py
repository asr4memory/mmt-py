from django.db import models
from django.utils.translation import gettext_lazy as _


class UploadedFile(models.Model):
    upload_job = models.ForeignKey(
        "upload_jobs.UploadJob", on_delete=models.CASCADE, related_name="uploaded_files"
    )
    filename = models.CharField(max_length=255, verbose_name=_("Filename"))
    size = models.BigIntegerField(default=0, verbose_name=_("Size"))
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
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.filename
