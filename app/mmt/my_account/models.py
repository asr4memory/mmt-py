from datetime import datetime, UTC
from pathlib import Path
from shutil import rmtree

from django.conf import settings
from django.contrib import admin
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


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/<username>/dpa/<filename>
    userdir = filename_safe(instance.user.username)
    return '{0}/dpa/{1}'.format(userdir, filename)


class FeatureFlag(models.Model):
    class Name(models.TextChoices):
        CHUNKED_UPLOAD = 'chunked_upload', _('Chunked upload')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feature_flags',
        verbose_name=_('User'),
    )
    name = models.CharField(max_length=50, choices=Name.choices, verbose_name=_('Name'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_flag')
        ]
        verbose_name = _('Feature flag')
        verbose_name_plural = _('Feature flags')

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
    dpa = models.FileField(
        blank=True,
        upload_to=user_directory_path,
        verbose_name=_('Data processing agreement'),
        help_text=_("Upload the user's data processing agreement here as a PDF file."),
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
    terms_accepted_version = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Terms version'),
        help_text=_('The latest terms of use version the user has accepted.'),
    )
    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Terms date'),
        help_text=_('When the user accepted the terms of use.'),
    )
    dpa_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('DPA date'),
        help_text=_('When the user accepted the Data Processing Agreement.'),
    )

    def is_flag_enabled(self, flag: str) -> bool:
        return self.feature_flags.filter(name=flag).exists()

    @property
    def safe_profile(self) -> Profile:
        profile, created = Profile.objects.get_or_create(user=self)
        return profile

    @property
    def full_name(self) -> str:
        """Needed for django-import-export"""
        return self.safe_profile.full_name

    @property
    def user_directory(self) -> Path:
        return settings.MMT_USER_FILES_DIR / filename_safe(self.username)

    def accept_terms(self):
        self.terms_accepted_version = settings.MMT_TERMS_VERSION
        self.terms_accepted_at = datetime.now(tz=UTC)

    def accept_dpa(self):
        self.dpa_accepted_at = datetime.now(tz=UTC)

    @property
    def has_accepted_terms(self) -> bool:
        return self.terms_accepted_version == settings.MMT_TERMS_VERSION

    @admin.display(boolean=True, description=_('External'))
    def is_external_user(self) -> bool:
        internal_domains = getattr(settings, 'MMT_INTERNAL_DOMAINS', [])
        return not any(self.email.endswith(domain) for domain in internal_domains)

    @admin.display(boolean=True, description=_('DPA file?'))
    def has_dpa_file(self):
        return bool(self.safe_profile.dpa)

    def has_to_agree_to_dpa(self) -> bool:
        return self.is_external_user() and self.dpa_accepted_at is None

    def make_user_directory(self) -> None:
        self.user_directory.mkdir(parents=True, exist_ok=True)

    def remove_user_directory(self) -> None:
        if self.user_directory.exists():
            rmtree(self.user_directory)
