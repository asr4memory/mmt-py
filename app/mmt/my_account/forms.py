from allauth.account.forms import LoginForm, SignupForm, ResetPasswordForm, ChangePasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import BaseUserCreationForm, UsernameField
from django.forms import ModelForm, RadioSelect, CharField
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
        super().__init__(*args, **kwargs, label_suffix="")

        if "login" in self.fields:
            self.fields["login"].label = _("Account name")


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix="")

        if "username" in self.fields:
            self.fields["username"].label = _("Account name")
            self.fields["username"].widget.attrs["placeholder"] = _("Account name")

        self.fields["email"].help_text = _(
            "<p>If possible, please use your institutional email address.</p>"
        )
        self.fields["password1"].help_text = _(
            "<p>The password must contain at least one uppercase letter, one lowercase letter, and one special character. It must also be at least 8 characters long.</p>"
        )

        name_field = CharField(max_length=255, label=_("Full name"), required=False)
        name_field.widget.attrs["placeholder"] = _("Firstname Lastname")
        self.fields["fullname"] = name_field

        self.order_fields(
            ["username", "email", "fullname", "password1", "password2", "address"]
        )

    def save(self, request):
        user = super().save(request)
        profile = user.safe_profile
        profile.full_name = request.POST.get("fullname", "")
        profile.save()
        return user


class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix="")


class CustomChangePasswordForm(ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix="")

        self.fields["password1"].help_text = _(
            "<p>The password must contain at least one uppercase letter, one lowercase letter, and one special character. It must also be at least 8 characters long.</p>"
        )
