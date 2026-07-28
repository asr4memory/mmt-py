from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase


class CreateGroupsCommandTestCase(TestCase):
    def test_command(self):
        call_command('creategroups')

        group_count = Group.objects.count()
        self.assertEqual(group_count, 2, 'Two groups are created')

        uploaders_group = Group.objects.first()
        self.assertEqual(uploaders_group.name, 'Uploaders', "Group name is 'Uploaders'")

        transcribers_group = Group.objects.last()
        self.assertEqual(
            transcribers_group.name, 'Transcribers', "Group name is 'Transcribers'"
        )

        uploaders_permissions = uploaders_group.permissions.all()
        perm_str = [perm.name for perm in uploaders_permissions]
        self.assertListEqual(
            perm_str,
            [
                'Can add processing request',
                'Can change processing request',
                'Can delete processing request',
                'Can view processing request',
                'Can add uploaded file',
                'Can change uploaded file',
                'Can delete uploaded file',
                'Can view uploaded file',
            ],
            'Group contains perms for processing requests and uploaded files',
        )

        transcribers_permissions = transcribers_group.permissions.all()
        perm_str = [perm.name for perm in transcribers_permissions]
        self.assertListEqual(
            perm_str,
            [
                'Can add transcript',
                'Can change transcript',
                'Can delete transcript',
                'Can view transcript',
            ],
            'Group contains perms for transcripts',
        )

        call_command('creategroups')

        group_count = Group.objects.count()
        self.assertEqual(group_count, 2, 'Command is idempotent, group count still 2')

        uploaders_group = Group.objects.first()
        self.assertEqual(
            uploaders_group.permissions.count(),
            8,
            'Uploaders group permission count is still the same',
        )

        transcribers_group = Group.objects.last()
        self.assertEqual(
            transcribers_group.permissions.count(),
            4,
            'Transcribers group permission count is still the same',
        )
