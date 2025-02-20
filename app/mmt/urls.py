from django.conf import settings
from django.conf.urls.i18n import i18n_patterns

from django.contrib import admin
from django.urls import path, include

import core.views as core_views


urlpatterns = i18n_patterns(
    path("admin/", admin.site.urls),
    path("account/", include("django.contrib.auth.urls")),
    path("account/", include("account.urls")),
    path("downloads/", include("downloads.urls")),
    path("pages/", include("pages.urls")),
    path("upload-jobs/", include("upload_jobs.urls")),
    path("uploaded-files/", include("uploaded_files.urls")),
    path("", core_views.welcome, name="welcome"),
)

if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
