from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Project, ProcessingRequest


ACCEPTED_FILES = ["video/*", "audio/*", "image/*", "model/vnd.mts", "application/mxf"]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description"]

        widgets = {
            "title": forms.TextInput(attrs={"placeholder": _("Name your project")}),
            "description": forms.Textarea(attrs={"placeholder": _("Briefly describe your project"), "rows": 5}),
        }


class UploadForm(forms.Form):
    files = forms.FileField(
        label=_("Files"),
        widget=MultipleFileInput(attrs={"accept": ",".join(ACCEPTED_FILES)}),
        required=True,
    )


class ProcessingRequestForm(forms.ModelForm):
    class Meta:
        model = ProcessingRequest
        fields = [
            "description",
            "language",
            "make_available_on_platform",
            "transcribe",
            "check_media_files",
            "replace_existing_files",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
