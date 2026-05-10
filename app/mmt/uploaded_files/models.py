from math import ceil
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import Project
from mmt.uploaded_files.utils import generate_file_md5



class UploadedFile(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        verbose_name=_('Project'),
    )
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    original_filename = models.CharField(
        max_length=255, verbose_name=_('Original filename')
    )
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
    def status(self) -> str:
        if self.has_file:
            return 'complete'
        if self.chunks.exists():
            return 'incomplete'
        return 'missing'

    @property
    def is_corrupt(self) -> bool | None:
        """Returns None if one of the checksums is missing."""
        if self.checksum_client == '' or self.checksum_server == '':
            return None

        return self.checksum_server != self.checksum_client

    @property
    def filename_altered(self) -> bool:
        return self.filename != self.original_filename

    @property
    def has_waveform(self) -> bool:
        try:
            self.waveform
            return True
        except ObjectDoesNotExist:
            return False

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
        "Remove actual file and any remaining chunk files. Call before deleting record."
        try:
            self.file_path.unlink()
        except FileNotFoundError:
            print(f'File {self.filename} does not exist.')
        for chunk in self.chunks.all():
            chunk.chunk_path.unlink(missing_ok=True)

    def assemble_chunks(self) -> None:
        missing = self.missing_chunk_indices()
        if missing:
            raise ValueError(f'Missing chunk indices: {missing}')

        tmp_path = self.file_path.with_name(self.file_path.name + '.tmp')
        chunks = list(self.chunks.all())
        try:
            with open(tmp_path, 'wb') as f:
                for chunk in chunks:
                    f.write(chunk.chunk_path.read_bytes())
            tmp_path.rename(self.file_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        for chunk in chunks:
            chunk.chunk_path.unlink(missing_ok=True)

        with transaction.atomic():
            self.chunks.all().delete()
            self.has_file = True
            self.save()

    def transferred_from_chunks(self) -> int:
        if not self.size:
            return 0
        total = ceil(self.size / settings.MMT_UPLOAD_CHUNK_SIZE)
        last_index = total - 1
        last_chunk_size = self.size - last_index * settings.MMT_UPLOAD_CHUNK_SIZE
        return sum(
            last_chunk_size if index == last_index else settings.MMT_UPLOAD_CHUNK_SIZE
            for index in self.chunks.values_list('index', flat=True)
        )

    def missing_chunk_indices(self) -> set[int]:
        total = ceil(self.size / settings.MMT_UPLOAD_CHUNK_SIZE)
        received = set(self.chunks.values_list('index', flat=True))
        return set(range(total)) - received

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


class FileChunk(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    index = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64, blank=True)

    def create_checksum(self) -> None:
        self.checksum = generate_file_md5(self.chunk_path)

    @property
    def chunk_path(self) -> Path:
        file_path = self.uploaded_file.file_path
        return file_path.with_name(file_path.name + f'.part.{self.index}')

    class Meta:
        ordering = ['index']
        constraints = [
            models.UniqueConstraint(
                fields=['uploaded_file', 'index'], name='unique_chunk'
            ),
        ]
