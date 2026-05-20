from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import Project


class UploadedFile(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        verbose_name=_('Project'),
    )
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    has_file = models.BooleanField(default=False, verbose_name=_('Has file'))
    size = models.BigIntegerField(default=0, verbose_name=_('Size'))
    media_type = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_('Media type')
    )
    checksum_server = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_('Server checksum')
    )
    checksum_client = models.CharField(
        max_length=255, blank=True, null=False, verbose_name=_('Client checksum')
    )
    duration = models.IntegerField(
        default=0,
        verbose_name=_('Duration'),
        help_text=_('Duration is calculated automatically with a background job.'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        ordering = ['created_at', 'filename']
        verbose_name = _('uploaded file')
        verbose_name_plural = _('uploaded files')
        constraints = [
            models.UniqueConstraint(
                fields=['project_id', 'filename'], name='unique_filename'
            ),
        ]

    @property
    def file_path(self) -> Path:
        return self.project.upload_directory / self.filename

    @property
    async def afile_path(self) -> Path:
        "Async version of file_path"
        project = await Project.objects.aget(pk=self.project_id)
        project_path = await project.aupload_directory
        return project_path / self.filename

    @property
    def is_corrupt(self) -> bool | None:
        """Returns None if one of the checksums is missing."""
        if self.checksum_client == '' or self.checksum_server == '':
            return None

        return self.checksum_server != self.checksum_client

    @property
    def has_waveform(self) -> bool:
        try:
            self.waveform
            return True
        except ObjectDoesNotExist:
            return False

    @property
    def status_human(self) -> str:
        if not self.has_file:
            return _('No file')

        if self.is_corrupt:
            return _('Corrupt')

        return _('Complete')

    def is_audio(self) -> bool:
        return self.media_type.startswith('audio')

    def is_video(self) -> bool:
        return self.media_type.startswith('video')

    def is_av_media(self) -> bool:
        return self.is_audio() or self.is_video()

    def update_has_file_field(self) -> bool:
        self.has_file = self.file_path.exists()
        self.save()
        return self.has_file

    def delete_file(self) -> None:
        "Remove actual file. Call before deleting record."
        try:
            self.file_path.unlink()
        except FileNotFoundError:
            print(f'File {self.filename} does not exist.')

    def __str__(self):
        return f'{self.project.title}: {self.filename}'


class Waveform(models.Model):
    uploaded_file = models.OneToOneField(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='waveform',
        verbose_name=_('Uploaded file'),
    )
    data = models.JSONField(verbose_name=_('Data'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('waveform')
        verbose_name_plural = _('waveforms')

    def __str__(self):
        return f'Waveform for {self.uploaded_file}'
