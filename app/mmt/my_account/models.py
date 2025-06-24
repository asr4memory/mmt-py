from pathlib import Path
from shutil import rmtree

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    """
    Represents a tag that describes or groups a user.
    One user can have many tags.
    """

    name = models.CharField(
        max_length=255, blank=False, null=False, unique=True, verbose_name=_("Name")
    )
    description = models.TextField(
        null=False, blank=True, default="", verbose_name=_("Description")
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name


class User(AbstractUser):
    tags = models.ManyToManyField(
        Tag,
        related_name="users",
        verbose_name=_("Tags"),
        help_text=_("Tags that describe or group the user"),
    )

    def upload_path(self) -> Path:
        return settings.MMT_USER_FILES_DIR / self.username / "uploads"

    def download_path(self) -> Path:
        return settings.MMT_USER_FILES_DIR / self.username / "downloads"

    def create_user_directories(self) -> None:
        self.upload_path().mkdir(parents=True, exist_ok=True)
        self.download_path().mkdir(parents=True, exist_ok=True)

    def destroy_user_directories(self) -> None:
        if self.upload_path().exists():
            rmtree(self.upload_path())

        if self.download_path().exists():
            rmtree(self.download_path())

    @property
    def safe_profile(self):
        profile, created = Profile.objects.get_or_create(user=self)
        return profile


class Profile(models.Model):
    LOCALE_ENGLISH = "en"
    LOCALE_GERMAN = "de"
    LOCALE_CHOICES = (
        (LOCALE_ENGLISH, _("English")),
        (LOCALE_GERMAN, _("German")),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("User")
    )
    full_name = models.CharField(
        max_length=255, blank=True, null=False, default="", verbose_name=_("Full name")
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
