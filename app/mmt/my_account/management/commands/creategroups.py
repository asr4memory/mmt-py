from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Generates initial groups"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        group, created = Group.objects.get_or_create(name="Uploaders")

        upload_job_ct = ContentType.objects.get(model="uploadjob")
        uploaded_file_ct = ContentType.objects.get(model="uploadedfile")

        group.permissions.add(*list(upload_job_ct.permission_set.all()))
        group.permissions.add(*list(uploaded_file_ct.permission_set.all()))
