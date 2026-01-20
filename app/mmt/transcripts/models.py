from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Transcript(models.Model):
    LANGUAGE_CHOICES = [
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
    ]

    uploaded_file = models.ForeignKey(
        'uploaded_files.UploadedFile',
        on_delete=models.CASCADE,
        related_name='transcripts',
        related_query_name='transcript',
        verbose_name=_('Uploaded file'),
    )
    label = models.CharField(max_length=255, verbose_name=_('Label'))
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='de',
        verbose_name=_('Language'),
        help_text=_('Select the language of the transcript.'),
    )
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
