from django.conf import settings


def core_constants(request):
    return {'APP_VERSION': settings.MMT_APP_VERSION}
