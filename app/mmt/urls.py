from django.conf import settings
from django.contrib import admin
from django.urls import include, path

import mmt.core.views as core_views

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("mmt.my_account.urls")),
    path("accounts/", include("allauth.urls")),
    path("projects/", include("mmt.projects.urls")),
    path("uploaded-files/", include("mmt.uploaded_files.urls")),
    path("tinymce/", include("tinymce.urls")),
    path("", core_views.welcome, name="welcome"),
    path("sentry-debug", trigger_error),
]

if settings.DJANGO_ENV == "development":
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
