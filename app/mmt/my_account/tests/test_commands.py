import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

UPLOADERS_PERMISSIONS = [
    'Can add processing request',
    'Can change processing request',
    'Can delete processing request',
    'Can view processing request',
    'Can add uploaded file',
    'Can change uploaded file',
    'Can delete uploaded file',
    'Can view uploaded file',
]

TRANSCRIBERS_PERMISSIONS = [
    'Can add transcript',
    'Can change transcript',
    'Can delete transcript',
    'Can view transcript',
    'Can add transcription job',
    'Can change transcription job',
    'Can delete transcription job',
    'Can view transcription job',
]


def permission_names(group):
    return [permission.name for permission in group.permissions.all()]


@pytest.mark.django_db
def test_creategroups_creates_both_groups_with_their_permissions():
    call_command('creategroups')

    assert Group.objects.count() == 2

    uploaders = Group.objects.get(name='Uploaders')
    transcribers = Group.objects.get(name='Transcribers')

    assert permission_names(uploaders) == UPLOADERS_PERMISSIONS
    assert permission_names(transcribers) == TRANSCRIBERS_PERMISSIONS


@pytest.mark.django_db
def test_creategroups_is_idempotent():
    call_command('creategroups')
    call_command('creategroups')

    assert Group.objects.count() == 2

    uploaders = Group.objects.get(name='Uploaders')
    transcribers = Group.objects.get(name='Transcribers')

    assert uploaders.permissions.count() == 8
    assert transcribers.permissions.count() == 8
