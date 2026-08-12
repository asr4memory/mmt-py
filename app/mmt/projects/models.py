import os
from pathlib import Path
from stat import S_ISDIR

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField

from mmt.core.models import TimestampedModel
from mmt.core.utils import filename_safe
from mmt.projects.checks import DirectoryIssue, ProjectCheckResult
from mmt.projects.utils import get_filename_suffix
from mmt.projects.validators import validate_filename_safe

User = get_user_model()


class Project(TimestampedModel):
    title = models.CharField(
        max_length=128,
        verbose_name=_('Title'),
        validators=[validate_filename_safe],
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects',
        related_query_name='project',
        verbose_name=_('User'),
    )
    description = models.TextField(
        blank=True, default='', verbose_name=_('Description')
    )
    downloadable_files_count = models.IntegerField(
        default=0,
        verbose_name=_('Downloads'),
        help_text=_('Cache field for number of files in download directory.'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('project')
        verbose_name_plural = _('projects')

    @property
    def directory_name(self) -> str:
        safe_name = filename_safe(self.title)
        date_suffix = get_filename_suffix(self.created_at)
        return f'{safe_name}.{date_suffix}'

    @property
    def project_directory(self) -> Path:
        return self.user.user_directory / self.directory_name

    @property
    def upload_directory(self) -> Path:
        return self.project_directory / 'upload'

    @property
    def download_directory(self) -> Path:
        return self.project_directory / 'download'

    @property
    async def aproject_directory(self) -> Path:
        "Async version of project_directory"
        user = await User.objects.aget(pk=self.user_id)
        result = user.user_directory / self.directory_name
        return result

    @property
    async def aupload_directory(self) -> Path:
        project_directory = await self.aproject_directory
        return project_directory / 'upload'

    def ensure_directories(self) -> None:
        """Create the project's upload and download directories if missing.

        Idempotent. Both are nested under project_directory, so creating them
        with parents=True creates project_directory too.
        """
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        self.download_directory.mkdir(parents=True, exist_ok=True)

    def check_directories(self) -> ProjectCheckResult:
        """Verify the project's required directories exist and are usable.

        Returns a :class:`ProjectCheckResult`; ``result.ok`` is True when the
        project, upload and download directories each exist, are directories
        and are readable, writable and executable. Report-only; use
        :meth:`ensure_directories` to create missing ones.
        """
        result = ProjectCheckResult()

        for label, path in (
            ('project', self.project_directory),
            ('upload', self.upload_directory),
            ('download', self.download_directory),
        ):
            try:
                stat = path.stat()
            except FileNotFoundError:
                result.issues.append(
                    DirectoryIssue(
                        label, 'missing', f'Directory does not exist: {path}'
                    )
                )
                continue
            except OSError as exc:
                result.issues.append(
                    DirectoryIssue(
                        label,
                        'stat_error',
                        f'Could not read directory metadata: {exc}',
                    )
                )
                continue

            if not S_ISDIR(stat.st_mode):
                result.issues.append(
                    DirectoryIssue(
                        label, 'not_a_directory', f'Path is not a directory: {path}'
                    )
                )
                continue

            if not os.access(path, os.R_OK):
                result.issues.append(
                    DirectoryIssue(
                        label, 'not_readable', f'Directory is not readable: {path}'
                    )
                )
            if not os.access(path, os.W_OK):
                result.issues.append(
                    DirectoryIssue(
                        label, 'not_writable', f'Directory is not writable: {path}'
                    )
                )
            if not os.access(path, os.X_OK):
                result.issues.append(
                    DirectoryIssue(
                        label, 'not_executable', f'Directory is not traversable: {path}'
                    )
                )

        return result

    def __repr__(self):
        return f'Project(title={self.title!r}, user_id={self.user_id!r})'

    def __str__(self):
        return f'{self.title}'


class ProcessingRequest(TimestampedModel):
    class Status(models.TextChoices):
        CREATED = 'created', _('Created')
        ACCEPTED = 'accepted', _('Started')
        REJECTED = 'rejected', _('Rejected')
        COMPLETED = 'completed', _('Completed')

    LANGUAGE_CHOICES = [
        (None, _('No selection')),
        ('de', _('German')),
        ('en', _('English')),
        ('fr', _('French')),
        ('es', _('Spanish')),
        ('it', _('Italian')),
        ('ja', _('Japanese')),
        ('zh', _('Chinese')),
        ('nl', _('Dutch')),
        ('uk', _('Ukrainian')),
        ('pt', _('Portuguese')),
        ('ar', _('Arabic')),
        ('cs', _('Czech')),
        ('ru', _('Russian')),
        ('pl', _('Polish')),
        ('hu', _('Hungarian')),
        ('fi', _('Finnish')),
        ('fa', _('Persian')),
        ('el', _('Greek')),
        ('tr', _('Turkish')),
        ('da', _('Danish')),
        ('he', _('Hebrew')),
        ('vi', _('Vietnamese')),
        ('ko', _('Korean')),
        ('ur', _('Urdu')),
        ('te', _('Telugu')),
        ('hi', _('Hindi')),
        ('ca', _('Catalan')),
        ('ml', _('Malayalam')),
        ('no', _('Norwegian Bokmål')),
        ('nn', _('Norwegian Nynorsk')),
        ('other', _('Other language')),
        ('mixed', _('Mixed language')),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='processing_requests',
        related_query_name='processing_request',
        verbose_name=_('Project'),
    )
    description = models.TextField(blank=True, default='', verbose_name=_('Note'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name=_('Status'),
    )
    admin_comment = HTMLField(
        blank=True,
        default='',
        verbose_name=_('Admin comment'),
        help_text=_('Optional comment by the administrator reviewing this request.'),
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        choices=LANGUAGE_CHOICES,
        verbose_name=_('Language'),
        help_text=_('Select the language associated with the media files.'),
    )

    make_available_on_platform = models.BooleanField(
        default=False,
        verbose_name=_('Make media files available on Oral-History.Digital'),
    )
    replace_existing_files = models.BooleanField(
        default=False,
        verbose_name=_('Replace existing media files on Oral-History.Digital'),
    )
    check_media_files = models.BooleanField(
        default=False, verbose_name=_('Check media files')
    )
    transcribe = models.BooleanField(
        default=False, verbose_name=_('Transcribe media files automatically')
    )

    uploaded_files = models.JSONField(default=list, verbose_name=_('Uploaded files'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('processing request')
        verbose_name_plural = _('processing requests')

        constraints = [
            models.CheckConstraint(
                condition=Q(make_available_on_platform=True)
                | Q(replace_existing_files=True)
                | Q(check_media_files=True)
                | Q(transcribe=True),
                name='one_action_checked',
                violation_error_message=_('At least one action must be checked.'),
            )
        ]

    def uploaded_files_count(self) -> int:
        return len(self.uploaded_files)

    # Short description is only used by Django Admin.
    # How does this work exactly: Referencing this method from here
    # and 'annotating' it?
    uploaded_files_count.short_description = _('Uploaded files count')

    @property
    def deletable(self) -> bool:
        return self.status != self.Status.ACCEPTED

    def __str__(self):
        return f'{self.project.title} {self.created_at}'
