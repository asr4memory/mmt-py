from django.conf import settings
from django.contrib import admin
from django.urls import include, path

import mmt.core.views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("mmt.my_account.urls")),
    path("accounts/", include("allauth.urls")),
    path("projects/", include("mmt.projects.urls")),
    path("uploaded-files/", include("mmt.uploaded_files.urls")),
    path("tinymce/", include("tinymce.urls")),
    path("", core_views.welcome, name="welcome"),
]

if settings.DJANGO_ENV == "development":
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
