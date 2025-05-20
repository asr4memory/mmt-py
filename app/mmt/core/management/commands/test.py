import platform

from django.core.management.commands.test import Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *test_labels, **options):
        print(f"Python version: {platform.python_version()}")
        return super().handle(*test_labels, **options)
