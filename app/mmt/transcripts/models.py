from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from mmt.core.models import TimestampedModel


# The languages WhisperX has an alignment model for, matching its
# DEFAULT_ALIGN_MODELS_TORCH and DEFAULT_ALIGN_MODELS_HF. A job in a language
# outside this set produces output without word timestamps and fails the
# ingest, so this list is the single source for the transcribe form's options
# and has to be updated when the service upgrades WhisperX.
WHISPERX_LANGUAGES = [
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
]


# Create your models here.
class Transcript(TimestampedModel):
    uploaded_file = models.ForeignKey(
        'uploaded_files.UploadedFile',
        on_delete=models.CASCADE,
        related_name='transcripts',
        related_query_name='transcript',
        verbose_name=_('Uploaded file'),
    )
    label = models.CharField(max_length=255, verbose_name=_('Label'))
    content = models.JSONField(
        default=dict,
        verbose_name=_('Content'),
        help_text=_('Paste in the whole transcript in JSON format.'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('transcript')
        verbose_name_plural = _('transcripts')

    def get_absolute_url(self):
        return reverse('transcripts:edit', kwargs={'pk': self.pk})

    def __str__(self):
        return f'{self.label} {self.created_at}'


class TranscriptionJob(models.Model):
    """A single transcription of one media file by the ASR service.

    Machine execution state, not a workflow ticket: the app creates a job,
    submits it to the service, polls it and stores the result as a Transcript.
    """

    PENDING = 'pending'
    SUBMITTED = 'submitted'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (SUBMITTED, _('Submitted')),
        (RUNNING, _('Running')),
        (SUCCEEDED, _('Succeeded')),
        (FAILED, _('Failed')),
    ]

    TERMINAL = (SUCCEEDED, FAILED)
    IN_PROGRESS = (SUBMITTED, RUNNING)

    # The semantic modifiers of the existing pill component.
    PILL_MODIFIERS = {
        PENDING: 'quiet',
        SUBMITTED: 'info',
        RUNNING: 'info',
        SUCCEEDED: 'success',
        FAILED: 'danger',
    }

    uploaded_file = models.ForeignKey(
        'uploaded_files.UploadedFile',
        on_delete=models.CASCADE,
        related_name='transcription_jobs',
        related_query_name='transcription_job',
        verbose_name=_('Uploaded file'),
    )
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transcription_jobs',
        verbose_name=_('Transcript'),
    )
    asr_job_id = models.CharField(
        max_length=32, blank=True, verbose_name=_('ASR job ID')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Status'),
    )
    progress = models.FloatField(default=0.0, verbose_name=_('Progress'))
    error = models.TextField(blank=True, verbose_name=_('Error'))
    language = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Language'),
        help_text=_('Empty means the service detects the language automatically.'),
    )
    diarize = models.BooleanField(default=False, verbose_name=_('Diarize'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Started at')
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Finished at')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('transcription job')
        verbose_name_plural = _('transcription jobs')

    @property
    def media_path(self) -> str:
        """The file's path relative to the media storage, as a POSIX string.

        The service resolves this against its own MEDIA_ROOT, which is the same
        directory as the app's MMT_USER_FILES_DIR.
        """
        relative = self.uploaded_file.file_path.relative_to(settings.MMT_USER_FILES_DIR)
        return relative.as_posix()

    @property
    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL

    @property
    def is_in_progress(self) -> bool:
        """Whether the service is working on the job.

        A pending job has not been submitted yet, so its progress carries no
        information either.
        """
        return self.status in self.IN_PROGRESS

    @property
    def progress_percent(self) -> int:
        return round(self.progress * 100)

    @property
    def pill_modifier(self) -> str:
        return self.PILL_MODIFIERS[self.status]

    def __str__(self):
        return f'Transcription of {self.uploaded_file.filename} ({self.status})'
