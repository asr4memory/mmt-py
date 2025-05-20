from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    LOCALE_ENGLISH = "en"
    LOCALE_GERMAN = "de"
    LOCALE_CHOICES = (
        (LOCALE_ENGLISH, _("English")),
        (LOCALE_GERMAN, _("German")),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_("Full name")
    )
    locale = models.CharField(
        max_length=2,
        choices=LOCALE_CHOICES,
        default=LOCALE_ENGLISH,
        verbose_name=_("Locale"),
    )

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")

    def __str__(self):
        return self.full_name


class User(AbstractUser):
    def upload_path(self) -> Path:
        # TODO: Use safe filename here
        return settings.BASE_DIR / "user_files" / self.username / "uploads"

    def download_path(self) -> Path:
        # TODO: Use safe filename here
        return settings.BASE_DIR / "user_files" / self.username / "downloads"

    def create_user_directories(self) -> None:
        user_directory = settings.BASE_DIR / "user_files" / self.username
        uploads_directory = user_directory / "uploads"
        downloads_directory = user_directory / "downloads"
        uploads_directory.mkdir(parents=True, exist_ok=True)
        downloads_directory.mkdir(parents=True, exist_ok=True)

    def create_profile(self) -> None:
        obj, created = Profile.objects.get_or_create(user=self)
