from django.utils import translation


class AccountLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        user = request.user
        if user.is_authenticated:
            profile = user.safe_profile
            translation.activate(profile.locale)
            request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
