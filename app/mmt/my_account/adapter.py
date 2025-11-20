from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.translation import get_language_from_request

from mmt.my_account.models import Profile

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """Customized social account adapter."""

    def save_user(self, request, sociallogin, form=None):
        """Save additional information into user profile."""
        user = super().save_user(request, sociallogin, form)

        profile = user.safe_profile
        profile.full_name = f"{user.first_name} {user.last_name}".strip()
        lang_code = get_language_from_request(request)
        assert lang_code in (Profile.LOCALE_GERMAN, Profile.LOCALE_ENGLISH)
        profile.locale = lang_code
        profile.save()

        return user
