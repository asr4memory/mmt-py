from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import get_language_from_request

from mmt.my_account.models import Profile
from mmt.my_account.tasks import send_rendered_email


class MyAccountAdapter(DefaultAccountAdapter):
    """Customized account adapter."""

    def send_mail(self, template_prefix, email, context):
        """Render the email in the request and send it in a retrying task."""
        request = allauth_context.request
        full_context = {
            'request': request,
            'email': email,
            'current_site': get_current_site(request),
            **context,
        }
        message = self.render_mail(template_prefix, email, full_context)
        html_body = next(
            (
                content
                for content, mimetype in getattr(message, 'alternatives', [])
                if mimetype == 'text/html'
            ),
            None,
        )
        send_rendered_email.delay(
            subject=message.subject,
            body=message.body,
            from_email=message.from_email,
            to=message.to,
            html_body=html_body,
        )


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """Customized social account adapter."""

    def save_user(self, request, sociallogin, form=None):
        """Save additional information into user profile."""
        user = super().save_user(request, sociallogin, form)

        profile = user.safe_profile
        profile.full_name = f'{user.first_name} {user.last_name}'.strip()
        lang_code = get_language_from_request(request)
        assert lang_code in (Profile.LOCALE_GERMAN, Profile.LOCALE_ENGLISH)
        profile.locale = lang_code
        profile.save()

        return user
