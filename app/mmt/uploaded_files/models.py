import logging
import os
from math import ceil
from pathlib import Path
from stat import S_ISREG

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from mmt.core.models import TimestampedModel
from mmt.core.utils import file_category
from mmt.projects.models import Project
from mmt.uploaded_files.checks import FileCheckResult, FileIssue

logger = logging.getLogger(__name__)


class UploadedFileQuerySet(models.QuerySet):
    def partial(self) -> UploadedFileQuerySet:
        """Files that received chunks but were never assembled into a file.

        Matches the 'incomplete' status (see :attr:`UploadedFile.status`):
        chunks present, not currently assembling, no assembled file.
        """
        return self.filter(
            has_file=False, assembling=False, chunks__isnull=False
        ).distinct()

    def corrupt(self) -> UploadedFileQuerySet:
        """Files where both checksums are known but disagree.

        Files still missing one of the checksums are not (yet) conclusive and
        are excluded; see :attr:`UploadedFile.is_corrupt`.
        """
        return (
            self.exclude(checksum_client='')
            .exclude(checksum_server='')
            .exclude(checksum_client=models.F('checksum_server'))
        )

    def checksum_ok(self) -> UploadedFileQuerySet:
        """Files where both checksums are known and agree."""
        return (
            self.exclude(checksum_client='')
            .exclude(checksum_server='')
            .filter(checksum_client=models.F('checksum_server'))
        )

    def unverified(self) -> UploadedFileQuerySet:
        """Files still missing at least one checksum."""
        return self.filter(models.Q(checksum_client='') | models.Q(checksum_server=''))


class UploadedFile(TimestampedModel):
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
    assembling = models.BooleanField(default=False, verbose_name=_('Assembling'))
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
    has_web_video = models.BooleanField(
        default=False,
        verbose_name=_('Has web video'),
        help_text=_(
            'A 480p web-friendly version is generated automatically with a '
            'background job for videos.'
        ),
    )

    objects = UploadedFileQuerySet.as_manager()

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
    def web_video_path(self) -> Path:
        """Path of the derived 480p web version of a video upload.

        The derived files live in a ``web/`` subdirectory beside the original,
        so the upload directory listing stays equal to the set of originals.
        The name is the full stored filename with ``.mp4`` appended rather than
        the stem with the suffix replaced, so two uploads that differ only in
        their extension do not collide.
        """
        return self.file_path.parent / 'web' / (self.filename + '.mp4')

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
        if self.assembling:
            return 'processing'
        if self.chunks.exists():
            return 'incomplete'
        return 'missing'

    @property
    def is_corrupt(self) -> bool | None:
        """Returns None if one of the checksums is missing."""
        if self.checksum_client == '' or self.checksum_server == '':
            return None

        return self.checksum_server != self.checksum_client

    def log_if_corrupt(self) -> None:
        """Emit a warning when the stored checksums disagree.

        No-op while either checksum is still missing. Callers should make sure
        both fields are current (e.g. via ``refresh_from_db``) before calling,
        since the client and server checksums are written by separate requests
        and may arrive in any order.
        """
        if self.is_corrupt:
            logger.warning(
                'Checksum mismatch for uploaded file %s (project %s, %s bytes): '
                'server=%s client=%s',
                self.pk,
                self.project_id,
                self.size,
                self.checksum_server,
                self.checksum_client,
            )

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

    def file_category(self) -> str:
        return file_category(self.media_type)

    def is_audio(self) -> bool:
        return self.file_category() == 'audio'

    def is_video(self) -> bool:
        return self.file_category() == 'video'

    def is_av_media(self) -> bool:
        return self.is_audio() or self.is_video()

    def stream_source(self) -> tuple[Path, str]:
        """Path and content type to serve for inline playback.

        Returns the derived web video only when the flag is set and the file is
        present on disk; if the derived file was removed after the flag was
        set, the original is served instead. Downloads always use
        :attr:`file_path` and never call this method.
        """
        if self.has_web_video and self.web_video_path.is_file():
            return self.web_video_path, 'video/mp4'
        return self.file_path, self.media_type

    def update_has_file_field(self) -> bool:
        self.has_file = self.file_path.exists()
        self.save()
        return self.has_file

    def check_file(self) -> FileCheckResult:
        """Verify the file on disk is consistent with this database record.

        Returns a :class:`FileCheckResult`; ``result.ok`` is True when the file
        exists, is a regular readable file and has the size recorded in the
        database. Does not verify checksums (see :attr:`is_corrupt`).
        """
        result = FileCheckResult()
        path = self.file_path

        try:
            stat = path.stat()
        except FileNotFoundError:
            if self.has_file:
                message = 'File is marked as present but does not exist on disk.'
            else:
                message = 'File does not exist on disk.'
            result.issues.append(FileIssue('missing', message))
            return result
        except OSError as exc:
            result.issues.append(
                FileIssue('stat_error', f'Could not read file metadata: {exc}')
            )
            return result

        if not S_ISREG(stat.st_mode):
            result.issues.append(
                FileIssue(
                    'not_a_regular_file', 'Path exists but is not a regular file.'
                )
            )

        if stat.st_size != self.size:
            result.issues.append(
                FileIssue(
                    'size_mismatch',
                    f'File size on disk ({stat.st_size} bytes) differs from the '
                    f'database ({self.size} bytes).',
                )
            )

        if not os.access(path, os.R_OK):
            result.issues.append(FileIssue('not_readable', 'File is not readable.'))

        if not self.has_file:
            result.issues.append(
                FileIssue(
                    'has_file_mismatch',
                    'File exists on disk but is not marked as present.',
                )
            )

        return result

    def delete_file(self) -> None:
        """Remove the file, the derived web video and any remaining chunk files.

        Call before deleting the record. The web video is removed regardless of
        :attr:`has_web_video`, so a derived file left behind by an interrupted
        transcode is cleaned up as well.
        """
        self.file_path.unlink(missing_ok=True)
        self.web_video_path.unlink(missing_ok=True)
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
                f.writelines(chunk.chunk_path.read_bytes() for chunk in chunks)
            tmp_path.rename(self.file_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        for chunk in chunks:
            chunk.chunk_path.unlink(missing_ok=True)

        with transaction.atomic():
            self.chunks.all().delete()
            self.has_file = True
            self.assembling = False
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


class Waveform(TimestampedModel):
    uploaded_file = models.OneToOneField(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='waveform',
        verbose_name=_('Uploaded file'),
    )
    data = models.JSONField(verbose_name=_('Data'))

    class Meta:
        verbose_name = _('waveform')
        verbose_name_plural = _('waveforms')

    def __str__(self):
        return f'Waveform for {self.uploaded_file}'


class FileChunk(TimestampedModel):
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    index = models.PositiveIntegerField()

    @property
    def chunk_path(self) -> Path:
        file_path = self.uploaded_file.file_path
        return file_path.parent / 'chunks' / (file_path.name + f'.part.{self.index}')

    class Meta:
        ordering = ['index']
        constraints = [
            models.UniqueConstraint(
                fields=['uploaded_file', 'index'], name='unique_chunk'
            ),
        ]
