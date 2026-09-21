from django import forms

from mmt.transcripts.models import Transcript


class TranscriptLabelForm(forms.ModelForm):
    """Validates the label of a transcript on its way in from a client."""

    class Meta:
        model = Transcript
        fields = ['label']
