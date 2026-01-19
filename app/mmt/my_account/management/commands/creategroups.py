from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Generates initial groups'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Create Uploaders group
        uploaders, created = Group.objects.get_or_create(name='Uploaders')

        processing_request_ct = ContentType.objects.get(model='processingrequest')
        uploaded_file_ct = ContentType.objects.get(model='uploadedfile')

        uploaders.permissions.add(*list(processing_request_ct.permission_set.all()))
        uploaders.permissions.add(*list(uploaded_file_ct.permission_set.all()))

        # Create Transcribers group
        transcribers, created = Group.objects.get_or_create(name='Transcribers')

        transcript_ct = ContentType.objects.get(model='transcript')

        transcribers.permissions.add(*list(transcript_ct.permission_set.all()))
