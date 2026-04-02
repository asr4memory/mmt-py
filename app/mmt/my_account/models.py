from pathlib import Path
from shutil import rmtree

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import filename_safe


class Tag(models.Model):
    """
    Represents a tag that describes or groups a user.
    One user can have many tags.
    """

    name = models.CharField(
        max_length=255, blank=False, null=False, unique=True, verbose_name=_('Name')
    )
    description = models.TextField(
        null=False, blank=True, default='', verbose_name=_('Description')
    )

    class Meta:
        ordering = ['name']
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def __str__(self):
        return self.name


class Profile(models.Model):
    LOCALE_ENGLISH = 'en'
    LOCALE_GERMAN = 'de'
    LOCALE_CHOICES = (
        (LOCALE_ENGLISH, _('English')),
        (LOCALE_GERMAN, _('German')),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('User')
    )
    full_name = models.CharField(
        max_length=255, blank=True, null=False, default='', verbose_name=_('Full name')
    )
    locale = models.CharField(
        max_length=2,
        choices=LOCALE_CHOICES,
        default=LOCALE_ENGLISH,
        verbose_name=_('Language'),
    )
    terms_accepted_version = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_('Accepted terms version')
    )
    terms_accepted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Terms accepted at')
    )

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __repr__(self):
        return f"Profile(full_name='{self.full_name}',locale='{self.locale}')"

    def __str__(self):
        return self.full_name


class User(AbstractUser):
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_(
            'Choose a username between 4 and 32 characters using only lowercase letters, numbers, underscores (_), or hyphens (-).'
        ),
        validators=[AbstractUser.username_validator],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='users',
        blank=True,
        verbose_name=_('Tags'),
        help_text=_('Tags that describe or group the user'),
    )
    upload_permission_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Upload permission requested at'),
        help_text=_(
            'When, if at all, the user has requested joining the Uploaders group'
        ),
    )

    @property
    def safe_profile(self) -> Profile:
        profile, created = Profile.objects.get_or_create(user=self)
        return profile

    @property
    def user_directory(self) -> Path:
        return settings.MMT_USER_FILES_DIR / filename_safe(self.username)

    @property
    def has_accepted_terms(self) -> bool:
        return self.safe_profile.terms_accepted_version == settings.TERMS_VERSION

    def make_user_directory(self) -> None:
        self.user_directory.mkdir(parents=True, exist_ok=True)

    def remove_user_directory(self) -> None:
        if self.user_directory.exists():
            rmtree(self.user_directory)
