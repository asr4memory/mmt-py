from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mmt.uploaded_files.models import UploadedFile

DEFAULT_MIN_AGE_HOURS = 24


class Command(BaseCommand):
    help = (
        'Remove partially uploaded files (those that still have chunks but no '
        'assembled file), including their chunk files on disk.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-age',
            type=int,
            default=DEFAULT_MIN_AGE_HOURS,
            metavar='HOURS',
            help=(
                'Only remove partial uploads not modified within the last HOURS '
                f'hours (default: {DEFAULT_MIN_AGE_HOURS}). Protects in-progress '
                'uploads.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List what would be removed without deleting anything.',
        )

    def handle(self, *args, **options):
        min_age = options['min_age']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(hours=min_age)

        partial_uploads = (
            UploadedFile.objects.partial()
            .filter(updated_at__lt=cutoff)
            .order_by('updated_at')
        )

        count = 0
        for uploaded_file in partial_uploads:
            if dry_run:
                self.stdout.write(
                    f'Would remove {uploaded_file} (last modified '
                    f'{uploaded_file.updated_at:%Y-%m-%d %H:%M}).'
                )
            else:
                uploaded_file.delete_file()
                uploaded_file.delete()
                self.stdout.write(f'Removed {uploaded_file}.')
            count += 1

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(f'{count} partial upload(s) would be removed.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Removed {count} partial upload(s).')
            )
