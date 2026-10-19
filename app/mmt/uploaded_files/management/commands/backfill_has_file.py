# TODO: Remove together with the update_has_file_field call in the detail view
# once the command has run on every deployment.
from django.core.management.base import BaseCommand

from mmt.uploaded_files.models import UploadedFile


class Command(BaseCommand):
    help = (
        'Set has_file on every uploaded file to whether the file exists on disk. '
        'One-off backfill for rows created before the field existed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report the affected files without changing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        count = 0
        for uploaded_file in UploadedFile.objects.select_related('project'):
            exists = uploaded_file.file_path.exists()
            if exists == uploaded_file.has_file:
                continue
            if dry_run:
                self.stdout.write(f'Would set has_file={exists} for {uploaded_file}.')
            else:
                uploaded_file.update_has_file_field()
                self.stdout.write(f'Set has_file={exists} for {uploaded_file}.')
            count += 1

        if dry_run:
            self.stdout.write(self.style.NOTICE(f'{count} file(s) would be updated.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated {count} file(s).'))
