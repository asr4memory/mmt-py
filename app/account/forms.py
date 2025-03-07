import re

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import BaseUserCreationForm, UsernameField
from django.core.exceptions import ValidationError
from django.forms import ModelForm, RadioSelect
from django.utils.translation import gettext_lazy as _

from .models import Profile

User = get_user_model()

username_format = re.compile(r"^[a-z]+_[a-z0-9]+$")


def validate_username(value):
    if len(value) < 4:
        raise ValidationError(
            _("%(value)s is too short"),
            params={"value": value},
        )
    if len(value) > 12:
        raise ValidationError(
            _("%(value)s is too long"),
            params={"value": value},
        )
    if not username_format.match(value):
        raise ValidationError(
            _("%(value)s does not have the right format"),
            params={"value": value},
        )


class RegisterForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        field_classes = {
            "username": UsernameField,
        }
        help_texts = {
            'username': _('Your username must be 4–12 characters long and must contain the archive id (if available, otherwise abbrevation of your institution) and your last name (separated with underscore), e.g. fub_musterfrau.'),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'fub_musterfrau'

    def clean_username(self):
        username = self.cleaned_data['username']
        validate_username(username)
        return username


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "locale"]
        widgets = {
            "locale": RadioSelect(),
        }
