from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation

whitelisted_paths = [
    reverse('account_logout'),
    reverse('account:accept_terms'),
    reverse('account:download-dpa'),
    reverse('account:dpa-sample'),
    reverse('account:edit_profile'),
    reverse('account:profile'),
    reverse('welcome'),
]


class AccountLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.user.is_authenticated:
            translation.activate(request.user.safe_profile.locale)
            request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


class TermsRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
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
