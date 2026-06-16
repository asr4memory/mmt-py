from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import filename_safe

from .models import ProcessingRequest, Project


def _content_type_accepted(content_type):
    for pattern in settings.MMT_ACCEPTED_FILES:
        if pattern.endswith('/*'):
            if content_type.startswith(pattern[:-1]):
                return True
        elif content_type == pattern:
            return True
    return False


class UploadedFileForm(forms.Form):
    filename = forms.CharField()
    content_type = forms.CharField()
    size = forms.IntegerField(min_value=1, max_value=settings.MMT_MAX_UPLOAD_SIZE)

    def clean_content_type(self):
        content_type = self.cleaned_data['content_type']
        if not _content_type_accepted(content_type):
            raise ValidationError(_('Unsupported content type.'))
        return content_type


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description']

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('Name your project')}),
            'description': forms.Textarea(
                attrs={'placeholder': _('Briefly describe your project'), 'rows': 5}
            ),
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        try:
            filename_safe(title)
        except ValueError:
            raise ValidationError(_('This title cannot be used as a project name. Please use letters or numbers.'))
        return title


class UploadForm(forms.Form):
    files = forms.FileField(
        label=_('Files'),
        widget=MultipleFileInput(
            attrs={'accept': ','.join(settings.MMT_ACCEPTED_FILES)}
        ),
        required=True,
    )


class ProcessingRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uploaded_files = self.instance.project.uploaded_files.all()
        self.fields['uploaded_files'] = forms.MultipleChoiceField(
            label=_('Uploaded files'),
            choices=[(file.filename, file.filename) for file in uploaded_files],
            widget=forms.CheckboxSelectMultiple(),
        )

    class Meta:
        model = ProcessingRequest
        fields = [
            'make_available_on_platform',
            'transcribe',
            'check_media_files',
            'replace_existing_files',
            'language',
            'description',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
