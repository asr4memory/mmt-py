from django.contrib.auth import get_user_model
from django.contrib.auth.forms import BaseUserCreationForm, UsernameField
from django.forms import ModelForm, RadioSelect
from django.utils.translation import gettext_lazy as _

from .models import Profile
from .validators import validate_username

User = get_user_model()


class RegisterForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        field_classes = {
            "username": UsernameField,
        }
        help_texts = {
            "username": _(
                "Your username must be 4–12 characters long and must contain the archive id (if available, otherwise abbrevation of your institution) and your last name (separated with underscore), e.g. fub_musterfrau."
            ),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        username_widget = self.fields["username"].widget
        username_widget.attrs["placeholder"] = "fub_musterfrau"
        username_widget.attrs["minlength"] = 4
        username_widget.attrs["maxlength"] = 12
        username_widget.attrs["pattern"] = "[a-z]+_[a-z]+"

        self.fields["password1"].widget.attrs["minlength"] = 8

        self.fields["password2"].widget.attrs["minlength"] = 8

    def clean_username(self):
        username = self.cleaned_data["username"]
        validate_username(username)
        return username


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "locale"]
        widgets = {
            "locale": RadioSelect(),
        }
