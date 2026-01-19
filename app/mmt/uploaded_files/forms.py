from django import forms
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['filename', 'media_type', 'size']


class TranscriptForm(forms.ModelForm):
    class Meta:
        model = Transcript
        fields = ['label', 'language', 'content']

        widgets = {
            'label': forms.TextInput(attrs={'placeholder': _('Name your transcript')}),
            'content': JSONEditorWidget,
        }
