from django.core.management.base import BaseCommand

from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import normalize_content


class Command(BaseCommand):
    help = (
        'Bring every stored transcript up to the current mmt-transcript format '
        'by running it through normalize_content. Idempotent: already-normalized '
        'transcripts are left unchanged (ids preserved).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without saving anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        upgraded = 0
        skipped = 0
        for transcript in Transcript.objects.all().iterator():
            try:
                normalized = normalize_content(transcript.content)
            except Exception as error:
                skipped += 1
                self.stderr.write(
                    self.style.ERROR(
                        f'Skipped transcript {transcript.pk} ({transcript.label}): '
                        f'{error}'
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    f'Would normalize transcript {transcript.pk} ({transcript.label}).'
                )
            else:
                transcript.content = normalized.model_dump()
                transcript.save(update_fields=['content'])
                self.stdout.write(
                    f'Normalized transcript {transcript.pk} ({transcript.label}).'
                )
            upgraded += 1

        verb = 'would be normalized' if dry_run else 'normalized'
        self.stdout.write(
            self.style.SUCCESS(
                f'{upgraded} transcript(s) {verb}, {skipped} skipped.'
            )
        )
