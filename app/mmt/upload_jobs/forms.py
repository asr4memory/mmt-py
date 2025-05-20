from django import forms
from django.utils.translation import gettext_lazy as _

ACCEPTED_FILES = ["video/*", "audio/*", "image/*", "model/vnd.mts", "application/mxf"]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class UploadJobForm(forms.Form):
    files = forms.FileField(
        label=_("Files"),
        widget=MultipleFileInput(attrs={"accept": ",".join(ACCEPTED_FILES)}),
        required=False,
    )
    title = forms.CharField(label=_("Title"), max_length=100)
    description = forms.CharField(
        label=_("Description"), widget=forms.Textarea, required=False
    )
    language = forms.ChoiceField(
        label=_("Language"),
        choices=[
            ("other", _("Other")),
            ("en", _("English")),
            ("de", _("German")),
            ("fr", _("French")),
            ("es", _("Spanish")),
            ("ru", _("Russian")),
            ("po", _("Polish")),
            ("uk", _("Ukrainian")),
        ],
        required=False,
    )
    make_available_on_platform = forms.BooleanField(
        label=_("Make available on platform"), required=False
    )
    transcribe = forms.BooleanField(label=_("Transcribe"), required=False)
    check_media_files = forms.BooleanField(label=_("Check media files"), required=False)
    replace_existing_files = forms.BooleanField(
        label=_("Replace existing files"), required=False
    )
