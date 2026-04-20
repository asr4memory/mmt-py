from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation

whitelisted_paths = [
    reverse('account:accept_terms'),
    reverse('account_logout'),
]


class AccountLocaleMiddleware:
    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if request.user.is_authenticated:
            translation.activate(request.user.safe_profile.locale)
            request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)

        return response

    async def __acall__(self, request):
        if request.user.is_authenticated:
            profile = await request.user.asafe_profile()
            translation.activate(profile.locale)
            request.LANGUAGE_CODE = translation.get_language()
        response = await self.get_response(request)

        return response


class TermsRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = request.user
        redirect_necessary = (
            user.is_authenticated
            and (not user.has_accepted_terms or user.has_to_agree_to_dpa())
            and request.path not in whitelisted_paths
        )
        if redirect_necessary:
            return redirect(reverse('account:accept_terms'))
        else:
            return response
