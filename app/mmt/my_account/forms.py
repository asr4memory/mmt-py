from allauth.account.forms import (
    ChangePasswordForm,
    LoginForm,
    ResetPasswordForm,
    SignupForm,
)
from django.forms import BooleanField, CharField, Form, ModelForm, RadioSelect
from django.utils.html import format_html
from django.utils.translation import get_language_from_request
from django.utils.translation import gettext_lazy as _

from mmt.my_account.models import Profile


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'locale']
        widgets = {
            'locale': RadioSelect(),
        }


class AcceptTermsForm(Form):
    def __init__(self, *args, terms=False, dpa=False, **kwargs):
        super().__init__(*args, **kwargs, label_suffix='')

        if terms:
            accept_terms_field = BooleanField(
                required=True, label=_('I agree to the terms of use')
            )
            self.fields['accept_terms_field'] = accept_terms_field

        if dpa:
            accept_dpa_field = BooleanField(
                required=True, label=_('I agree to the data processing agreement')
            )
            self.fields['accept_dpa_field'] = accept_dpa_field

        self.order_fields(['accept_terms_field', 'accept_dpa_field'])


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
        profile.save()

        user.accept_terms()
        user.save()
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
