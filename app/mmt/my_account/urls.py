from django.urls import path

from . import views

app_name = 'account'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path(
        'profile/upload-permission/', views.upload_permission, name='upload-permission'
    ),
    path('profile/accept-terms/', views.accept_terms, name='accept_terms'),
    path('profile/dpa-sample/', views.dpa_sample, name='dpa-sample'),
    path('profile/dpa/', views.download_dpa, name='download-dpa'),
    path('debug/', views.debug, name='debug'),
]
