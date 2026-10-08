from django.conf import settings
from django.contrib import admin
from django.urls import include, path

import mmt.core.views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('mmt.my_account.urls')),
    path('accounts/', include('allauth.urls')),
    path('jobs/', include('mmt.jobs.urls')),
    path('projects/', include('mmt.projects.urls')),
    path('transcripts/', include('mmt.transcripts.urls')),
    path('uploaded-files/', include('mmt.uploaded_files.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('', core_views.welcome, name='welcome'),
    path('sentry-debug/', core_views.trigger_error),
]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))

if settings.SILK_ENABLED:
    urlpatterns.append(path('silk/', include('silk.urls', namespace='silk')))
