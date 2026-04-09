from datetime import datetime, UTC

from allauth.account.forms import (
    ChangePasswordForm,
    LoginForm,
    ResetPasswordForm,
    SignupForm,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import BaseUserCreationForm, UsernameField
from django.forms import BooleanField, CharField, Form, ModelForm, RadioSelect
from django.utils.html import format_html
from django.utils.translation import get_language_from_request
from django.utils.translation import gettext_lazy as _

from mmt.my_account.models import Profile
from mmt.my_account.validators import validate_username

User = get_user_model()


class RegisterForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        field_classes = {
            'username': UsernameField,
        }
        help_texts = {
            'username': _(
                'Choose a username between 4 and 32 characters using only lowercase letters, numbers, underscores (_), or hyphens (-).'
            ),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        username_widget = self.fields['username'].widget
        username_widget.attrs['minlength'] = 4
        username_widget.attrs['maxlength'] = 32
        username_widget.attrs['pattern'] = '[a-z0-9_-]+'

        self.fields['password1'].widget.attrs['minlength'] = 8

        self.fields['password2'].widget.attrs['minlength'] = 8

    def clean_username(self):
        username = self.cleaned_data['username']
        validate_username(username)
        return username


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'locale']
        widgets = {
            'locale': RadioSelect(),
        }


class AcceptTermsForm(Form):
    accept_terms_field = BooleanField(
        required=True, label=_('I agree to the terms of use')
    )


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix='')

        if 'login' in self.fields:
            self.fields['login'].label = _('Account name')


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix='')

        if 'username' in self.fields:
            self.fields['username'].label = _('Account name')
            self.fields['username'].widget.attrs['placeholder'] = _('Account name')
            self.fields['username'].help_text = _(
                "<p>If possible, please use a combination of your institution's abbreviation and your surname, for example: fub_doe. Only lowercase letters, numbers, underscores and hyphens are permitted, with a minimum of 4 and a maximum of 32 characters.</p>"
            )

        self.fields['email'].help_text = _(
            '<p>If possible, please use your institutional email address.</p>'
        )
        self.fields['password1'].help_text = _(
            '<p>The password must contain at least one uppercase letter, one lowercase letter, and one special character. It must also be at least 8 characters long.</p>'
        )

        name_field = CharField(max_length=255, required=True, label=_('Full name'))
        name_field.widget.attrs['placeholder'] = _('Firstname Lastname')
        self.fields['fullname'] = name_field

        accept_terms_field = BooleanField(
            required=True,
            label=format_html(
                '{} <a href="{}" target="_blank">{}</a>',
                _('I agree to the'),
                _('https://www.oral-history.digital/en/mitmachen/mmt'),
                _('terms of use'),
            ),
        )
        self.fields['accept_terms'] = accept_terms_field

        self.order_fields(
            ['username', 'email', 'fullname', 'password1', 'password2', 'accept_terms']
        )

    def save(self, request):
        user = super().save(request)
        profile = user.safe_profile
        profile.full_name = request.POST.get('fullname', '')

        lang_code = get_language_from_request(request)
        assert lang_code in (Profile.LOCALE_GERMAN, Profile.LOCALE_ENGLISH)
        profile.locale = lang_code

        profile.terms_accepted_version = settings.MMT_TERMS_VERSION
        profile.terms_accepted_at = datetime.now(tz=UTC)

        profile.save()
        return user


class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix='')


class CustomChangePasswordForm(ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, label_suffix='')

        self.fields['password1'].help_text = _(
            '<p>The password must contain at least one uppercase letter, one lowercase letter, and one special character. It must also be at least 8 characters long.</p>'
        )
