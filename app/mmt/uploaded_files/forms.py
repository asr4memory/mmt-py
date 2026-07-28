import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import normalize_content
from mmt.transcripts.validators import validate_whisper_input
from mmt.uploaded_files.models import UploadedFile


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['filename', 'media_type', 'size']


class TranscriptForm(forms.ModelForm):
    CONTENT_SOURCE_CHOICES = [
        ('json', _('Paste JSON')),
        ('file', _('Upload file')),
    ]

    content_source = forms.ChoiceField(
        choices=CONTENT_SOURCE_CHOICES,
        initial='json',
        required=False,
        widget=forms.RadioSelect,
        label=_('Content source'),
    )
    content_file = forms.FileField(
        required=False,
        label=_('Content file'),
        widget=forms.ClearableFileInput(attrs={'accept': '.json,application/json'}),
    )

    class Meta:
        model = Transcript
        fields = ['label', 'content']

        widgets = {
            'label': forms.TextInput(attrs={'placeholder': _('Name your transcript')}),
            'content': JSONEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only one of the two sources is filled in, so neither is required on
        # its own; clean() enforces that the selected source is present.
        self.fields['content'].required = False

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('content_source') or 'json'

        if source == 'file':
            # The pasted JSON editor is irrelevant in file mode; discard any
            # error it may have produced.
            self.errors.pop('content', None)
            cleaned_data.pop('content', None)

            uploaded = cleaned_data.get('content_file')
            if not uploaded:
                self.add_error('content_file', _('Please upload a JSON file.'))
            else:
                try:
                    cleaned_data['content'] = json.loads(uploaded.read())
                except json.JSONDecodeError, UnicodeDecodeError:
                    self.add_error(
                        'content_file',
                        _('The uploaded file is not valid JSON.'),
                    )
                else:
                    try:
                        validate_whisper_input(cleaned_data['content'])
                    except ValidationError as error:
                        self.add_error('content_file', error)
                    else:
                        cleaned_data['content'] = normalize_content(
                            cleaned_data['content']
                        ).model_dump()
        else:
            if cleaned_data.get('content') in (None, ''):
                self.add_error('content', _('Please paste the transcript JSON.'))
            else:
                try:
                    validate_whisper_input(cleaned_data['content'])
                except ValidationError as error:
                    self.add_error('content', error)
                else:
                    cleaned_data['content'] = normalize_content(
                        cleaned_data['content']
                    ).model_dump()

        return cleaned_data
