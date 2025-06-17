from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .filesystem import filename_safe


class UploadJob(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upload_jobs",
        verbose_name=_("User"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(
        blank=True, default="", verbose_name=_("Description")
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

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated_at"))

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("upload job")
        verbose_name_plural = _("upload jobs")

    def directory_name(self) -> str:
        safe_title = filename_safe(self.title)
        date_suffix = self.created_at.strftime(".%Y-%m-%dT%H%M%SZ")
        return safe_title + date_suffix

    def __str__(self):
        return self.title
