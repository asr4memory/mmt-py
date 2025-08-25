from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase


class CreateGroupsCommandTestCase(TestCase):
    def test_command(self):
        call_command("creategroups")

        group_count = Group.objects.count()
        self.assertEqual(group_count, 1, "One group is created")

        group = Group.objects.first()
        self.assertEqual(group.name, "Uploaders", "Group name is 'Uploaders'")

        permissions = group.permissions.all()
        perm_str = [perm.name for perm in permissions]
        self.assertListEqual(
            perm_str,
            [
                "Can add processing request",
                "Can change processing request",
                "Can delete processing request",
                "Can view processing request",
                "Can add project",
                "Can change project",
                "Can delete project",
                "Can view project",
                "Can add uploaded file",
                "Can change uploaded file",
                "Can delete uploaded file",
                "Can view uploaded file",
            ],
            "Group contains perms for projects and uploaded files",
        )

        call_command("creategroups")

        group_count = Group.objects.count()
        self.assertEqual(group_count, 1, "Command is idempotent, group count still 1")
        group = Group.objects.first()
        self.assertEqual(group.permissions.count(), 12, "Permission count is still the same")
