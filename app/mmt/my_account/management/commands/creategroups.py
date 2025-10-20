from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Generates initial groups"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        group, created = Group.objects.get_or_create(name="Uploaders")

        processing_request_ct = ContentType.objects.get(model="processingrequest")
        project_ct = ContentType.objects.get(model="project")
        uploaded_file_ct = ContentType.objects.get(model="uploadedfile")

        group.permissions.add(*list(processing_request_ct.permission_set.all()))
        group.permissions.add(*list(project_ct.permission_set.all()))
        group.permissions.add(*list(uploaded_file_ct.permission_set.all()))
