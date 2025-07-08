from django.utils.translation import get_language_from_request


def get_preferred_language(request) -> str:
    return get_language_from_request(request)
