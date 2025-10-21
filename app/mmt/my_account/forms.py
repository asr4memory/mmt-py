from allauth.account.forms import LoginForm, SignupForm
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
                "Choose a username between 4 and 32 characters using only lowercase letters, numbers, underscores (_), or hyphens (-)."
            ),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        username_widget = self.fields["username"].widget
        username_widget.attrs["minlength"] = 4
        username_widget.attrs["maxlength"] = 32
        username_widget.attrs["pattern"] = "[a-z0-9_-]+"

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


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label_suffix = ""

        if "login" in self.fields:
            self.fields["login"].label = _("Account name")


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label_suffix = ""
