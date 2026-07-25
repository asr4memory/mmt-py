from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Transcript(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('transcript')
        verbose_name_plural = _('transcripts')

    def get_absolute_url(self):
        return reverse('transcripts:edit', kwargs={'pk': self.pk})

    def __str__(self):
        return f'{self.label} {self.created_at}'
