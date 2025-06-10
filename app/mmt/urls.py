from django.conf import settings
from django.conf.urls.i18n import i18n_patterns

from django.contrib import admin
from django.urls import path, include

import mmt.core.views as core_views


urlpatterns = i18n_patterns(
    path("admin/", admin.site.urls),
    path("account/", include("mmt.my_account.urls")),
    path('accounts/', include('allauth.urls')),
    path("downloads/", include("mmt.downloads.urls")),
    path("pages/", include("mmt.pages.urls")),
    path("upload-jobs/", include("mmt.upload_jobs.urls")),
    path("uploaded-files/", include("mmt.uploaded_files.urls")),
    path("", core_views.welcome, name="welcome"),
)

if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
