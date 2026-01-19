from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from tinymce.models import HTMLField

from mmt.core.utils import filename_safe
from mmt.projects.utils import get_filename_suffix

User = get_user_model()


class Project(models.Model):
    title = models.CharField(max_length=128, verbose_name=_('Title'))
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    downloadable_files_count = models.IntegerField(
        default=0,
        verbose_name=_('Downloadable files count'),
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

    def rename_directory_from(self, old_path: Path) -> Path:
        result = old_path.rename(self.project_directory)
        return result

    def __str__(self):
        return f'{self.title}'


class ProcessingRequest(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
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

    def __str__(self):
        return f'{self.project.title} {self.created_at}'
