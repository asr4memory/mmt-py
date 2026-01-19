from django import forms
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript


class TranscriptForm(forms.ModelForm):
    class Meta:
        model = Transcript
        fields = ['label', 'language', 'content']

        widgets = {
            'label': forms.TextInput(attrs={'placeholder': _('Name your transcript')}),
            'content': JSONEditorWidget,
        }
